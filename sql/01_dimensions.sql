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
FROM vendor_golden;

INSERT INTO dim_vendor (VendorAccount, VendorName, MigrationStatus)
VALUES ('UNKNOWN', '** Vendor not in master **', 'Exception');

-------------------------------------------------------------------

DROP TABLE IF EXISTS dim_item;

SELECT
    ItemNumber,
    Description,
    ItemGroup,
    UoM,
    CAST(StandardCost AS DECIMAL(12, 1)) AS StandardCost
INTO dim_item
FROM stg_item;

INSERT INTO dim_item (ItemNumber, Description, ItemGroup)
VALUES ('UNKNOWN', '** Item not in master **', 'UNKNOWN');

-------------------------------------------------------------------

DROP TABLE IF EXISTS dim_date;

WITH dates AS (
    SELECT CAST('2025-01-01' AS DATE) AS [Date]
    UNION ALL
    SELECT DATEADD(DAY, 1, [Date])
    FROM dates
    WHERE [Date] < '2026-12-31'
)
SELECT
    [Date],
    YEAR([Date])                                        AS [Year],
    DATEPART(QUARTER, [Date])                           AS QuarterNum,
    'Q' + CAST(DATEPART(QUARTER, [Date]) AS VARCHAR(1)) AS [Quarter],
    DATENAME(MONTH, [Date])                             AS [MonthName],
    FORMAT([Date], 'yyyy-MM')                           AS YearMonth
INTO dim_date
FROM dates
OPTION (MAXRECURSION 0);