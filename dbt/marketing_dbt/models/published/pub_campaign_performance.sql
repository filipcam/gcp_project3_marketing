{{
    config(
        materialized='table',
        description='Published data product. Zagregowana skuteczność kampanii. Stable interface.'
    )
}}

with campaign_performance as (

    select *
    from {{ ref('int_campaign_performance') }}

),

final as (

    select
        campaign_id,
        campaign_name,
        channel,
        objective,
        target_segment,
        start_date,
        end_date,
        budget_amount,
        status,
        owner_team,

        -- Metryki mediowe
        total_impressions,
        total_clicks,
        total_cost_amount,
        total_sessions,
        total_add_to_cart,

        -- Metryki sprzedażowe (okno kampanii)
        total_orders,
        total_items_sold,
        total_revenue,

        -- Wskaźniki
        ctr,
        cpc,
        cvr,
        cost_per_sale,

        -- Segment wydajności
        case
            when total_impressions = 0 then 'no_reach'
            when total_clicks      = 0 then 'no_clicks'
            when total_items_sold  = 0 then 'traffic_only'
            else 'converting'
        end as performance_segment,

        current_timestamp() as _dbt_loaded_at

    from campaign_performance

)

select * from final
