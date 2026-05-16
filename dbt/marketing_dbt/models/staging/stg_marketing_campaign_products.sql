with source as (

    select * from {{ source('marketing_raw', 'marketing_campaign_products') }}

),

cleaned as (

    select
        campaign_id,
        book_id,
        promo_type,
        discount_pct,
        featured_flag,
        promo_price,
        load_date,
        generated_at,
        source_file,
        current_timestamp() as _dbt_loaded_at
    from source
    where campaign_id is not null
      and book_id is not null

)

select * from cleaned