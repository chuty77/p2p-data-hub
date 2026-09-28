use P2PDataHub
GO
/* 
Requerimiento: un solo resultado con dos columnas, el nombre de la tabla y su cantidad de filas, para stg_vendor, 
stg_po_line, stg_receipt, stg_invoice y vendor_xref.
Resultado esperado: 43, 372, 327, 336, 43.
Por qué: confirma que lo que salió de Python es lo que llegó a SQL Server.
*/
SELECT 'stg_vendor' as table_name, count(*) as Rows from stg_vendor
union all
select 'stg_po_line', COUNT(*) from stg_po_line
union all
select 'stg_receipt', COUNT(*) from stg_receipt
union all
select 'stg_invoice', COUNT(*) from stg_invoice
union all
select 'vendor_xref', COUNT(*) from vendor_xref

/*
table_name	Rows
stg_vendor	43
stg_po_line	372
stg_receipt	327
stg_invoice	336
vendor_xref	43
*/



/*
Órdenes con proveedor inexistente
Requerimiento: listar las líneas de órdenes de compra (número de PO, número de línea y código de proveedor) 
cuyo proveedor no existe.
*/

select p.[PurchaseOrderNumber], p.[LineNumber], p.[VendorAccount]
from [P2PDataHub].[dbo].[stg_po_line] p
left join [P2PDataHub].[dbo].[vendor_xref] v
on p.[VendorAccount]   = v.[LegacyVendorCode]
where v.[VendorAccount] is null


/*
PurchaseOrderNumber	LineNumber	VendorCode
PO-25007	1	LV9999
PO-25088	1	LV9999
PO-25088	2	LV9999
*/


/*
Ejercicio 3: Órdenes con item inexistente
Requerimiento: igual que el anterior, pero para items: líneas de órdenes cuyo 
ItemNumber no existe en el maestro de items.
Resultado esperado: 1 línea.
*/


select p.[PurchaseOrderNumber], p.[LineNumber], p.[ItemNumber]
from stg_po_line p
left join stg_item i
on p.[ItemNumber] = i.[ItemNumber]
where i.[ItemNumber] is null
/*
PurchaseOrderNumber	LineNumber	ItemNumber
PO-25040	1	ITM-9999
*/

/*
Ejercicio 4: La xref en acción
Requerimiento: para los proveedores que se unieron por Tax ID, mostrar el código viejo,
la cuenta nueva de D365 a la que se traduce, y cuántas líneas de órdenes de compra tenía cada uno.
Pistas: necesitas unir órdenes con la xref, filtrar por el tipo de equivalencia y agrupar.
*/

select v.[LegacyVendorCode], v.[VendorAccount], COUNT(*)  as count_lines
from stg_po_line p 
 join vendor_xref v
on v.[LegacyVendorCode] = p.[VendorAccount]
where v.[MatchType] = 'Merged by Tax ID'
group by v.[LegacyVendorCode], v.[VendorAccount]
order by count_lines DESC



