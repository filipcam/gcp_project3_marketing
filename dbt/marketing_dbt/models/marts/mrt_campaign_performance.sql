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
        coalesce(total_impressions, 0)   as total_impressions,
        coalesce(total_clicks, 0)        as total_clicks,
        coalesce(total_cost_amount, 0)   as total_cost_amount,
        coalesce(total_sessions, 0)      as total_sessions,
        coalesce(total_add_to_cart, 0)   as total_add_to_cart,

        -- Metryki sprzedażowe z domeny Sales
        coalesce(total_orders, 0)        as total_orders,
        coalesce(total_items_sold, 0)    as total_items_sold,

        -- Wskaźniki
        coalesce(ctr, 0)            as ctr,
        coalesce(cpc, 0)            as cpc,
        coalesce(cvr, 0)            as cvr,
        coalesce(cost_per_sale, 0)  as cost_per_sale,

        case
            when coalesce(total_impressions, 0) = 0 then 'no_reach'
            when coalesce(total_clicks, 0) = 0      then 'no_clicks'
            when coalesce(total_items_sold, 0) = 0  then 'traffic_only'
            else 'converting'
        end as performance_segment,

        current_timestamp() as _dbt_loaded_at

    from campaign_performance

)

select * from final