{{
    config(
        materialized='table',
        description='Published data product. Atrybucja sprzedaży per kampania i książka. Stable interface for Sales domain.'
    )
}}


-- Atrybucja sprzedaży: kampania → book_id → rzeczywista sprzedaż w oknie kampanii.
-- Zastąpienie source top_products (MVP) → stg_book_daily_sales (book_daily_sales).
-- Sprzedaż agregowana per book_id w przedziale start_date – end_date kampanii.
-- has_sales_data = true oznacza że dla danej książki znaleziono transakcje w oknie kampanii.


with campaign_performance as (

    select *
    from {{ ref('int_campaign_performance') }}

),

campaign_products as (

    select
        campaign_id,
        book_id,
        promo_type,
        featured_flag
    from {{ ref('stg_marketing_campaign_products') }}

),

-- Agregacja sprzedaży per book_id × kampania (okno czasowe)
book_sales_in_window as (

    select
        cp.campaign_id,
        ds.book_id,
        sum(ds.orders_count)       as total_orders,
        sum(ds.items_sold)         as total_items_sold,
        sum(ds.gross_sales_amount) as total_revenue
    from campaign_products cp
    inner join {{ ref('stg_book_daily_sales') }} ds
        using (book_id)
    inner join {{ ref('stg_marketing_campaigns') }} c
        using (campaign_id)
    where ds.sales_date between c.start_date and c.end_date
    group by
        cp.campaign_id,
        ds.book_id

),

final as (

    select
        -- Klucze
        cp.campaign_id,
        cp.book_id,

        -- Kampania
        p.campaign_name,
        p.channel,
        p.objective,
        p.target_segment,
        p.start_date,
        p.end_date,
        p.status,
        p.budget_amount,
        p.owner_team,

        -- Produkt
        cp.promo_type,
        cp.featured_flag,

        -- Flaga sprzedaży (zastępuje title, author_name, category, format)
        case
            when bs.book_id is not null then true
            else false
        end as has_sales_data,

        -- Sprzedaż per książka w oknie kampanii
        -- NULL zachowany celowo: brak danych ≠ sprzedaż zerowa
        bs.total_orders,
        bs.total_items_sold,
        bs.total_revenue,

        -- Metryki mediowe kampanii (kontekst)
        coalesce(p.total_impressions,  0) as total_impressions,
        coalesce(p.total_clicks,       0) as total_clicks,
        coalesce(p.total_cost_amount,  0) as total_cost_amount,

        -- Wskaźniki atrybucji
        p.ctr,
        p.cpc,
        p.cost_per_sale,

        current_timestamp() as _dbt_loaded_at

    from campaign_products cp
    left join campaign_performance  p  using (campaign_id)
    left join book_sales_in_window  bs using (campaign_id, book_id)

)

select * from final