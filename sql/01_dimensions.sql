

DROP TABLE IF EXISTS dim_vendor;


SELECT
    VendorAccount,
    VendorCode AS LegacyVendorCode,
    VendorName,
    TaxID,
    Country,
    Currency,
    PaymentTerms,
    Email,
    Status,
    MigrationStatus
INTO dim_vendor
FROM vendor_golden



INSERT INTO dim_vendor (VendorAccount, VendorName, MigrationStatus)
VALUES ('UNKNOWN', '** Vendor not in master **', 'Exception')


drop table if exists dim_item


select 
    ItemNumber,
    Description,
    ItemGroup,
    UoM,
    CAST(StandardCost AS decimal(12, 1)) AS StandardCost
    INTO dim_item
    FROM stg_item;


 
 insert into dim_item(ItemNumber, Description, ItemGroup) values ('UNKNOWN', '** Item not in master **', 'UNKNOWN')


 drop table if exists dim_date


 with dates as(
      select cast('2025-01-01' as DATE) as [Date]
      union all

      select DATEADD(DAY,1,[Date])
      from dates
      where [Date] < '2026-12-31' 
)
SELECT
    [Date],
    YEAR([Date]) AS [YEAR],
    DATEPART(QUARTER, [Date]) AS QuarterNum,
    'Q' + CAST(DATEPART(QUARTER, [Date]) AS varchar(1)) AS [QUARTER],
    DATENAME(MONTH,[Date]) AS [MONTHNAME],
    FORMAT(DATE, 'yyyy-MM') as YearMonth
    into dim_date
    from dates 
    OPTION (MAXRECURSION 0);
  


    