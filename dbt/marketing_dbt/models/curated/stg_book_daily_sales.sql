-- Źródło: publishing-mesh-sales.sales_products.book_daily_sales
-- Zastępuje tymczasowe źródło top_products (MVP).
-- Dostarcza dzienną sprzedaż per book_id do warstwy curated.

with source as (

    select * from {{ source('sales', 'book_daily_sales') }}

),

cleaned as (

    select
        -- klucze
        book_id,
        cast(sales_date as date) as sales_date,

        -- atrybuty książki (denormalizacja ze źródła)
        title,
        author_name,
        category,
        format,

        -- metryki dzienne
        orders_count                                  as orders_count,
        items_sold                                    as items_sold,
        round(cast(gross_sales_amount as numeric), 2) as gross_sales_amount

    from source
    where sales_date is not null
      and book_id    is not null

)

select * from cleaned
