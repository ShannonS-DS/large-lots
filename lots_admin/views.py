from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from operator import __or__ as OR
from functools import reduce
from lots_admin.models import Application, Lot, ApplicationStep, Review, ApplicationStatus, DenialReason
from .look_ups import DENIAL_REASONS, APPLICATION_STATUS
from datetime import datetime
import csv
import json
from django import forms

def lots_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                login(request, user)
                return HttpResponseRedirect(reverse('lots_admin'))
    else:
        form = AuthenticationForm()
    return render(request, 'lots_login.html', {'form': form})

def lots_logout(request):
    logout(request)
    return HttpResponseRedirect('/')

@login_required(login_url='/lots-login/')
def lots_admin_map(request):
    applied_pins = set()
    for lot in Lot.objects.all():
        applied_pins.add(lot.pin)

    pins_str = ",".join(["'%s'" % a.replace('-','').replace(' ','') for a in applied_pins])
    return render(request, 'admin-map.html', {'applied_pins': pins_str})

@login_required(login_url='/lots-login/')
def lots_admin(request):
    # applications = Application.objects.filter(pilot=settings.CURRENT_PILOT)
    # applications_before_four = Application.objects.filter(Q(status__step=2) | Q(status__step=3))
    # applications_at_four = Application.objects.filter(status__step=4)

    application_status_list = ApplicationStatus.objects.filter(application__pilot=settings.CURRENT_PILOT)

    return render(request, 'admin.html', {
        'application_status_list': application_status_list,
        'selected_pilot': settings.CURRENT_PILOT,
        'pilot_info': settings.PILOT_INFO,
        # 'applications_before_four': applications_before_four,
        # 'applications_at_four': applications_at_four
        })

@login_required(login_url='/lots-login/')
def pilot_admin(request, pilot):
    applications = Application.objects.filter(pilot=pilot)
    return render(request, 'admin.html', {
        'applications': applications,
        'selected_pilot': pilot,
        'pilot_info': settings.PILOT_INFO})

@login_required(login_url='/lots-login/')
def csv_dump(request, pilot):
    response = HttpResponse(content_type='text/csv')
    now = datetime.now().isoformat()
    response['Content-Disposition'] = 'attachment; filename=Large_Lots_Applications_%s_%s.csv' % (pilot, now)
    applications = Application.objects.filter(pilot=pilot)
    header = [
        'ID',
        'Date received',
        'First Name',
        'Last Name',
        'Organization',
        'Owned Address',
        'Owned Full Address',
        'Owned PIN',
        'Deed Image URL',
        'Contact Address',
        'Phone',
        'Email',
        'Received assistance',
        'Lot PIN',
        'Lot Address',
        'Lot Full Address',
        'Lot Image URL',
        'Lot Planned Use',
    ]
    rows = []
    for application in applications:
        owned_address = '%s %s %s %s' % \
            (getattr(application.owned_address, 'street', ''),
            getattr(application.owned_address, 'city', ''),
            getattr(application.owned_address, 'state', ''),
            getattr(application.owned_address, 'zip_code', ''))
        contact_address = '%s %s %s %s' % \
            (getattr(application.contact_address, 'street', ''),
            getattr(application.contact_address, 'city', ''),
            getattr(application.contact_address, 'state', ''),
            getattr(application.contact_address, 'zip_code', ''))
        for lot in application.lot_set.all():
            addr = getattr(lot.address, 'street', '').upper()
            addr_full = '%s %s %s %s' % \
                (getattr(lot.address, 'street', ''),
                getattr(lot.address, 'city', ''),
                getattr(lot.address, 'state', ''),
                getattr(lot.address, 'zip_code', ''))
            pin = lot.pin
            image_url = 'https://pic.datamade.us/%s.jpg' % pin.replace('-', '')
            lot_use = lot.planned_use


            rows.append([
                application.id,
                application.received_date.strftime('%Y-%m-%d %H:%m %p'),
                application.first_name,
                application.last_name,
                application.organization,
                getattr(application.owned_address, 'street', '').upper(),
                owned_address,
                application.owned_pin,
                application.deed_image.url,
                contact_address,
                application.phone,
                application.email,
                application.how_heard,
                pin,
                addr,
                addr_full,
                image_url,
                lot_use,
            ])
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response

@login_required(login_url='/lots-login/')
def pdfviewer(request):
    return render(request, 'pdfviewer.html')

@login_required(login_url='/lots-login/')
def deny_application(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    review = Review.objects.filter(application=application_status).latest('id')
    return render(request, 'deny_application.html', {
        'application_status': application_status,
        'review': review
        })

@login_required(login_url='/lots-login/')
def deny_submit(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    application_status.current_step = None
    application_status.save()
    return HttpResponseRedirect(reverse('lots_admin'))

@login_required(login_url='/lots-login/')
def deed_check(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)

    # Delete last Review, if someone hits "no, go back" on deny page.
    Review.objects.filter(application=application_status, step_completed=2).delete()
    application_status.denied = False
    application_status.save()
    return render(request, 'deed_check.html', {
        'application_status': application_status
        })

@login_required(login_url='/lots-login/')
def deed_check_submit(request, application_id):
    if request.method == 'POST':
        application_status = ApplicationStatus.objects.get(id=application_id)
        user = request.user
        name = request.POST.get('name', 'off')
        address = request.POST.get('address', 'off')
        church = request.POST.get('church')
        # Move to step 3 of review process.
        if (name == 'on' and address == 'on' and church == '2'):
            step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['location'], public_status='approved', step=3)
            application_status.current_step = step
            application_status.save()

            review = Review(reviewer=user, email_sent=False, application=application_status, step_completed=2)
            review.save()

            return HttpResponseRedirect('/application-review/step-3/%s/' % application_status.id)
        # Deny application.
        else:
            if (church == '1'):
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['church'])
            elif (name == 'off' and address == 'on'):
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['name'])
            elif (name == 'on' and address == 'off'):
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['address'])
            else:
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['name-address'])
            review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=application_status, step_completed=2)
            review.save()

            application_status.denied = True
            application_status.save()

            return HttpResponseRedirect('/deny-application/%s/' % application_status.id)

@login_required(login_url='/lots-login/')
def location_check(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    # Delete last ReviewStatus, if someone hits "no, go back" on deny page.
    Review.objects.filter(application=application_status, step_completed=3).delete()
    application_status.denied = False
    application_status.save()
    # Location of the applicant's property.
    owned_pin = application_status.application.owned_pin

    # Location of the lot.
    lot_pin = application_status.lot.pin

    return render(request, 'location_check.html', {
        'application_status': application_status,
        'owned_pin': owned_pin,
        'lot_pin': lot_pin
        })

@login_required(login_url='/lots-login/')
def location_check_submit(request, application_id):
    if request.method == 'POST':
        application_status = ApplicationStatus.objects.get(id=application_id)
        user = request.user
        block = request.POST.get('block', 'off')

        if (block == 'on'):
            # Create a new review for completing this step.
            review = Review(reviewer=user, email_sent=False, application=application_status, step_completed=3)
            review.save()

            # Are there other applicants on this property?
            lot_pin = application_status.lot.pin
            other_applicants = ApplicationStatus.objects.filter(lot=lot_pin, denied=False)
            applicants_list = list(other_applicants)

            if (len(applicants_list) > 1):
                # If there are other applicants: move application to Step 4.
                step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['multi'], public_status='approved', step=4)
                application_status.current_step = step
                application_status.save()

                return HttpResponseRedirect(reverse('lots_admin'))
            else:
                # No other applicants: move application to Step 6.
                step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='approved', step=6)
                application_status.current_step = step
                application_status.save()

                return HttpResponseRedirect(reverse('lots_admin'))
        else:
            # Deny application, since applicant does not live on same block as lot.
            reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['block'])
            rev_status = Review(reviewer=user, email_sent=True, denial_reason=reason, application=application_status, step_completed=3)
            rev_status.save()
            application_status.denied = True
            application_status.save()

            return HttpResponseRedirect('/deny-application/%s/' % application_status.id)

@login_required(login_url='/lots-login/')
def multiple_applicant_check(request, application_id):
    application = Application.objects.get(id=application_id)

     # Delete last ReviewStatus, if someone hits "no, go back" on deny page.
    ReviewStatus.objects.filter(application=application, step_completed=4).delete()
    application.denied = False
    application.save()

    # Location of the applicant's property.
    owned_pin = application.owned_pin

    # Location(s) of properties the applicant applied for.
    applied_pins = [l.pin for l in application.lot_set.all()]

    # Are there other applicants on this property?
    applicants = Application.objects.filter(lot__pin__in=applied_pins).filter(denied=False)
    applicants_list = list(applicants)

    # Location(s) of properties of other applicants who applied for the same property.
    other_owned_pins = [app.owned_pin for app in applicants_list ]
    other_owned_pins.remove(owned_pin)

    return render(request, 'multiple_applicant_check.html', {
        'application': application,
        'owned_pin': owned_pin,
        'applied_pins': applied_pins,
        'applicants_list': applicants_list,
        'other_owned_pins': other_owned_pins
        })

@login_required(login_url='/lots-login/')
def multiple_location_check_submit(request, application_id):
    if request.method == 'POST':
        application = Application.objects.get(id=application_id)
        user = request.user
        adjacent = request.POST.get('adjacent')

        if (adjacent == '2'):
            # Deny application, since another applicant is adjacent to the property.
            reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['adjacent'])
            rev_status = ReviewStatus(reviewer=user, email_sent=True, denial_reason=reason, application=application, step_completed=4)
            rev_status.save()
            application.denied = True
            application.save()

            return HttpResponseRedirect('/deny-application/%s/' % application.id)

        elif (adjacent == '3'):
            # Application goes to Step 5: lottery.
            application_status, created = ApplicationStatus.objects.get_or_create(description=APPLICATION_STATUS['lottery'], public_status='approved', step=5)
            application.status = application_status
            application.save()
            rev_status = ReviewStatus(reviewer=user, email_sent=False, application=application, step_completed=4)
            rev_status.save()

            return HttpResponseRedirect(reverse('lots_admin'))
        else:
            # Move application to Step 6.
            application_status, created = ApplicationStatus.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='approved', step=6)
            application.status = application_status
            application.save()
            rev_status = ReviewStatus(reviewer=user, email_sent=False, application=application, step_completed=4)
            rev_status.save()

            # Deny other applicants.
            # Location(s) of properties the applicant applied for.
            applied_pins = [l.pin for l in application.lot_set.all()]
            applicants = Application.objects.filter(lot__pin__in=applied_pins).filter(denied=False)
            applicants_list = list(applicants)
            applicants_list.remove(application)

            for a in applicants_list:
                ReviewStatus.objects.filter(application=a, step_completed=4).delete()
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['adjacent'])
                rev_status = ReviewStatus(reviewer=user, email_sent=True, denial_reason=reason, application=a, step_completed=4)
                rev_status.save()
                a.denied = True
                a.status = None
                a.save()

            return HttpResponseRedirect(reverse('lots_admin'))

@login_required(login_url='/lots-login/')
def lottery(request):
    applications = Application.objects.filter(status__step=5)

    # All applications in a lottery.
    applications_list = list(applications)

    # All lots in a lottery; all applicants associated with those lots.
    applied_pins = []
    application_obj = {}
    for a in applications_list:
        applied_pins += [l.pin for l in a.lot_set.all()]
        for l in a.lot_set.all():
            application_obj[a] = l.pin

    print(application_obj)
    lot_pins = list(set(applied_pins))
    lots = Lot.objects.filter(pin__in=lot_pins)
    lots_list = list(lots)

    return render(request, 'lottery.html', {
        'application_obj': application_obj,
        'lots_list': lots_list
        })

@login_required(login_url='/lots-login/')
def lottery_submit(request):
    if request.method == 'POST':
        user = request.user
        winners = request.POST.getlist('winner')
        winners_id = [int(a) for a in winners]

        winning_apps = Application.objects.filter(id__in=winners_id)
        winning_apps_list = list(winning_apps)

        # Move lottery winners to Step 6.
        for a in winning_apps:
            # Move each application to Step 6.
            application_status, created = ApplicationStatus.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='approved', step=6)
            a.status = application_status
            a.save()

            # Create a review status.
            rev_status = ReviewStatus(reviewer=user, email_sent=False, application=a, step_completed=5)
            rev_status.save()

        return HttpResponseRedirect(reverse('lots_admin'))


@login_required(login_url='/lots-login/')
def review_status_log(request, application_id):
    application = ApplicationStatus.objects.get(id=application_id)
    reviews = Review.objects.filter(application=application)
    status = ApplicationStep.objects.all()
    return render(request, 'review_status_log.html', {
        'application': application,
        'reviews': reviews,
        'status': status
        })

@login_required(login_url='/lots-login/')
def alderman_advance_submit(request):
    if request.method == 'POST':
        user = request.user
        advance = request.POST.getlist('advance')
        advanced_applications_id = [int(a) for a in advance]
        applications = Application.objects.filter(id__in=advanced_applications_id)
        applications_list = list(applications)

        for a in applications:
            # Move each application to Step 7.
            application_status, created = ApplicationStatus.objects.get_or_create(description=APPLICATION_STATUS['EDS'], public_status='approved', step=7)
            a.status = application_status
            a.save()

            # Create a review status.
            rev_status = ReviewStatus(reviewer=user, email_sent=False, application=a, step_completed=6)
            rev_status.save()

        return HttpResponseRedirect(reverse('lots_admin'))
