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
    select * from {{ ref('int_campaign_performance') }}
),

book_attribution as (
    select * from {{ ref('int_campaign_book_attribution') }}
),

final as (
    select
        ba.campaign_id,
        ba.book_id,

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
        ba.promo_type,
        ba.featured_flag,

        -- Sprzedaż per książka
        ba.total_orders      is not null as has_sales_data,
        ba.total_orders,
        ba.total_items_sold,
        ba.total_revenue,

        -- Metryki mediowe kampanii (kontekst)
        p.total_impressions,
        p.total_clicks,
        p.total_cost_amount,
        p.ctr,
        p.cpc,
        p.cost_per_sale,

        current_timestamp() as _dbt_loaded_at

    from book_attribution ba
    left join campaign_performance p using (campaign_id)
)

select * from final