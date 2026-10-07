use P2PDataHub
go 


drop table if exists fact_po_line;

select 
    CONCAT(p.PurchaseOrderNumber, '-', p.LineNumber) as  POLineKey,
    p.PurchaseOrderNumber,
    p.LineNumber,
    COALESCE(x.VendorAccount, 'UNKNOWN') AS VendorAccount,
    COALESCE(i.ItemNumber, 'UNKNOWN') AS ItemNumber, 
    CAST(p.OrderDate AS DATE) AS OrderDate,
    p.Site,
    CAST(p.OrderedQuantity AS DECIMAL(12, 2))                AS OrderedQty,
    CAST(p.UnitPrice AS DECIMAL(12, 2))                      AS UnitPrice,
    CAST(p.OrderedQuantity * p.UnitPrice AS DECIMAL(14, 2))  AS POAmount
INTO fact_po_line
FROM stg_po_line p
LEFT JOIN vendor_xref x ON x.LegacyVendorCode = p.VendorAccount
LEFT JOIN stg_item i    ON i.ItemNumber = p.ItemNumber;
     
----------------------------------------------------------


DROP TABLE IF EXISTS fact_receipt;

SELECT
    ReceiptNumber,
    CONCAT(PurchaseOrderNumber, '-', LineNumber)  AS POLineKey,
    CAST(ReceivedQuantity AS DECIMAL(12, 2))      AS ReceivedQty,
    CAST(ReceiptDate AS DATE)                     AS ReceiptDate
INTO fact_receipt
FROM stg_receipt;

-------------------------------------------------------------------



DROP TABLE IF EXISTS fact_invoice;

SELECT
    ROW_NUMBER() OVER (ORDER BY v.InvoiceNumber, v.PurchaseOrderNumber, v.LineNumber) AS InvoiceLineID,
    v.InvoiceNumber,
    COALESCE(x.VendorAccount, 'UNKNOWN')                            AS VendorAccount,
    CONCAT(v.PurchaseOrderNumber, '-', v.LineNumber)                AS POLineKey,
    CAST(v.InvoiceQuantity AS DECIMAL(12, 2))                       AS InvoiceQty,
    CAST(v.InvoiceUnitPrice AS DECIMAL(12, 2))                      AS InvoiceUnitPrice,
    CAST(v.InvoiceQuantity * v.InvoiceUnitPrice AS DECIMAL(14, 2))  AS InvoiceAmount,
    CAST(v.InvoiceDate AS DATE)                                     AS InvoiceDate
INTO fact_invoice
FROM stg_invoice v
LEFT JOIN vendor_xref x ON x.LegacyVendorCode = v.VendorAccount;



SELECT COUNT(*) FROM fact_po_line;   -- 372
SELECT COUNT(*) FROM fact_receipt;   -- 327
SELECT COUNT(*) FROM fact_invoice;   -- 336
SELECT VendorAccount, COUNT(*) FROM fact_po_line WHERE VendorAccount = 'UNKNOWN' GROUP BY VendorAccount;  -- 3
SELECT ItemNumber, COUNT(*) FROM fact_po_line WHERE ItemNumber = 'UNKNOWN' GROUP BY ItemNumber;       -- 1


DROP TABLE IF EXISTS fact_three_way_match;

WITH receipts AS (
    SELECT POLineKey, SUM(ReceivedQty) AS ReceivedQty
    FROM fact_receipt
    GROUP BY POLineKey
),
inv AS (
    SELECT f.*,
           ROW_NUMBER() OVER (PARTITION BY VendorAccount, InvoiceNumber, POLineKey
                              ORDER BY InvoiceLineID) AS DupRank
    FROM fact_invoice f
),
inv_cum AS (
    SELECT i.*,
           SUM(CASE WHEN DupRank = 1 THEN InvoiceQty ELSE 0 END)
               OVER (PARTITION BY POLineKey ORDER BY InvoiceLineID
                     ROWS UNBOUNDED PRECEDING) AS CumInvoicedQty
    FROM inv i
)
SELECT
    c.InvoiceLineID, c.InvoiceNumber, c.VendorAccount, c.POLineKey, c.InvoiceDate,
    p.ItemNumber, p.OrderedQty, p.UnitPrice AS POUnitPrice,
    COALESCE(r.ReceivedQty, 0) AS ReceivedQty,
    c.InvoiceQty, c.InvoiceUnitPrice, c.InvoiceAmount,
    CAST((c.InvoiceUnitPrice - p.UnitPrice) / p.UnitPrice AS DECIMAL(9, 4))   AS PriceVariancePct,
    CAST((c.InvoiceUnitPrice - p.UnitPrice) * c.InvoiceQty AS DECIMAL(14, 2)) AS PriceVarianceAmount,
    CASE
        WHEN c.DupRank > 1                                           THEN 'Duplicate invoice'
        WHEN c.VendorAccount = 'UNKNOWN'                             THEN 'Unknown vendor'
        WHEN COALESCE(r.ReceivedQty, 0) = 0                          THEN 'No receipt'
        WHEN c.CumInvoicedQty > r.ReceivedQty                        THEN 'Qty variance'
        WHEN ABS(c.InvoiceUnitPrice - p.UnitPrice) / p.UnitPrice > 0.05 THEN 'Price variance'
        ELSE 'Matched'
    END AS MatchStatus
INTO fact_three_way_match
FROM inv_cum c
JOIN fact_po_line p   ON p.POLineKey = c.POLineKey
LEFT JOIN receipts r  ON r.POLineKey = c.POLineKey;


SELECT COUNT(*) FROM fact_three_way_match;  -- 336

SELECT MatchStatus,
       COUNT(*)                                           AS InvoiceLines,
       SUM(InvoiceAmount)                                 AS Amount,
       CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS DECIMAL(5, 1)) AS PctOfLines
FROM fact_three_way_match
GROUP BY MatchStatus
ORDER BY InvoiceLines DESC;