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