{{
    config(
        materialized='table',
        description='Published data product. Stable interface for other domains.'
    )
}}

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

sales as (

    select
        book_id,
        title,
        author_name,
        category,
        format,
        total_orders,
        total_items_sold
    from {{ source('sales', 'top_products') }}

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
        s.title,
        s.author_name,
        s.category,
        s.format,

        -- Sprzedaż per książka
        coalesce(s.total_orders, 0)     as total_orders,
        coalesce(s.total_items_sold, 0) as total_items_sold,

        -- Metryki mediowe kampanii (kontekst)
        coalesce(p.total_impressions, 0)  as total_impressions,
        coalesce(p.total_clicks, 0)       as total_clicks,
        coalesce(p.total_cost_amount, 0)  as total_cost_amount,

        -- Wskaźniki atrybucji
        coalesce(p.ctr, 0)           as ctr,
        coalesce(p.cpc, 0)           as cpc,
        coalesce(p.cost_per_sale, 0) as cost_per_sale,

        current_timestamp() as _dbt_loaded_at

    from campaign_products cp
    left join campaign_performance p using (campaign_id)
    left join sales s               using (book_id)

)

select * from final