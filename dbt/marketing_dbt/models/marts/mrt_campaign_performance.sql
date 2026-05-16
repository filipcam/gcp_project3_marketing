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

        coalesce(total_impressions, 0) as total_impressions,
        coalesce(total_clicks, 0) as total_clicks,
        coalesce(total_cost_amount, 0) as total_cost_amount,
        coalesce(total_sessions, 0) as total_sessions,
        coalesce(total_add_to_cart, 0) as total_add_to_cart,
        coalesce(total_conversions, 0) as total_conversions,

        coalesce(ctr, 0) as ctr,
        coalesce(cpc, 0) as cpc,
        coalesce(cvr, 0) as cvr,

        case
            when coalesce(total_impressions, 0) = 0 then 'no_reach'
            when coalesce(total_clicks, 0) = 0 then 'no_clicks'
            when coalesce(total_conversions, 0) = 0 then 'traffic_only'
            else 'converting'
        end as performance_segment,

        current_timestamp() as _dbt_loaded_at

    from campaign_performance

)

select * from final