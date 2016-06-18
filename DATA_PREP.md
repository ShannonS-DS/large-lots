### CartoDB Data prep

**Data sources**

* [Cook County Parcel Files](https://datacatalog.cookcountyil.gov/GIS-Maps/ccgisdata-Parcel-2012/e62c-6rz8)
* [Addresses in Chicago by PIN](https://datacatalog.cookcountyil.gov/GIS-Maps/ccgisdata-Address-Point-Chicago/jev2-4wjs)
* [City-Owned Land Inventory](https://data.cityofchicago.org/Community-Economic-Development/City-Owned-Land-Inventory/aksk-kvfp)
* [Chicago Community Areas](https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas-current-/cauq-8yn6)

**Transform coordinates for downloaded shapefiles**

```bash 
$ ogr2ogr -t_srs EPSG:4326 chicago_addresses.shp addressPointChi.shp
$ ogr2ogr -t_srs EPSG:4326 cook_county_parcels.shp Parcel2012_County.shp
$ ogr2ogr -t_srs EPSG:4326 community_areas.shp CommAreas.shp
```

**Load in shapefiles using ``shp2pgsql``**

```bash 
$ shp2pgsql -I -s 4326 cook_county_parcels.shp parcels | psql -U <db_user> -d <db_name>
$ shp2pgsql -I -s 4326 chicago_addresses.shp chicago_addresses | psql -U postgres -d wopr
```

**Load Land Inventory using ``csvsql`` (from [csvkit](https://csvkit.readthedocs.io/))**

```bash
$ cat land_inventory.csv | \
    (echo "pin14,street_number,street_dir,street_name,\
    street_type,sq_ft,ward,community_area,zoning_classification,\
    tif_district" ; tail -n +2) | \
    csvsql --db "postgresql://<db_user>:@localhost:5432/<db_name>" \
    --table land_inventory --insert
```

**Flag which parcels are city owned**

```sql
=> ALTER TABLE parcels ADD COLUMN city_owned BOOLEAN;
=> ALTER TABLE parcels ALTER COLUMN city_owned SET DEFAULT FALSE;
=> UPDATE parcels 
      SET city_owned = TRUE 
      WHERE pin14 IN (
          SELECT replace(pin14, '-', '') FROM land_inventory
      );
```

**Create table for just parcels in East Garfield Park**

```sql
=> CREATE TABLE egp_parcels AS 
      SELECT p.pin14, p.geom, p.city_owned 
          FROM parcels AS p 
          JOIN community_areas 
              ON ST_Within(p.geom, community_areas.geom) 
          WHERE community_areas.community = 'EAST GARFIELD PARK';
```

**Add a few extra columns for address info and residential zoning flag**

```sql
=> ALTER TABLE egp_parcels ALTER COLUMN street_number TYPE integer;
=> ALTER TABLE egp_parcels ALTER COLUMN street_name TYPE character varying(24);
=> ALTER TABLE egp_parcels ALTER COLUMN street_dir TYPE character varying(14);
=> ALTER TABLE egp_parcels ALTER COLUMN street_type TYPE character varying(14);
=> ALTER TABLE egp_parcels ALTER COLUMN zip_code TYPE character varying(5);
=> ALTER TABLE egp_parcels ALTER COLUMN sq_ft TYPE INTEGER;
=> ALTER TABLE egp_parcels ADD COLUMN residential boolean;
=> ALTER TABLE egp_parcels ALTER COLUMN residential SET DEFAULT FALSE;
```

**Add info from Land Inventory**

```sql 
=> UPDATE egp_parcels 
      SET street_number=subquery.street_number, 
          street_dir=subquery.street_dir, 
          street_name=subquery.street_name, 
          street_type=subquery.street_type, 
          zoning_classification=subquery.zoning_classification,
          sq_ft=subquery.sq_ft 
      FROM (
          SELECT 
              street_number, 
              street_dir, 
              street_name, 
              street_type, 
              zoning_classification, 
              replace(pin14, '-', '') as pin,
              sq_ft 
          FROM land_inventory 
      ) AS subquery 
      WHERE egp_parcels.pin14 = subquery.pin;
```

**Add residential flag**

```sql
=> UPDATE egp_parcels AS e 
       SET residential = TRUE 
       WHERE e.zoning_classification LIKE '%RS-1%' 
           OR e.zoning_classification LIKE '%RS-2%' 
           OR e.zoning_classification LIKE '%RS-3%' 
           OR e.zoning_classification LIKE '%RT-3.5%' 
           OR e.zoning_classification LIKE '%RT-4%' 
           OR e.zoning_classification LIKE '%RT-4A%' 
           OR e.zoning_classification LIKE '%RM-4.5%' 
           OR e.zoning_classification LIKE '%RM-5%' 
           OR e.zoning_classification LIKE '%RM-5.5%' 
           OR e.zoning_classification LIKE '%RM-6%' 
           OR e.zoning_classification LIKE '%RM-6.5%';
```

**Add address info from addresses table**

```sql
=> UPDATE egp_parcels 
      SET street_number=subquery.street_number, 
          street_dir=subquery.street_dir, 
          street_name=subquery.street_name, 
          street_type=subquery.street_type,
          zip_code=subquery.zip_code
      FROM (
          SELECT stnameprd AS street_dir, 
                 cast(addrnocom as integer) AS street_number, 
                 stname AS street_name, 
                 stnamepot AS street_type, 
                 pin,
                 zip5 as zip_code
          FROM chicago_addresses
          ) AS subquery 
      WHERE egp_parcels.pin14 = subquery.pin;
```

