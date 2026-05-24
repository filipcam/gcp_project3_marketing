with source as (

    select * from {{ source('marketing_raw', 'ext_marketing_campaign_products') }}

),

cleaned as (

    select
        campaign_id,
        book_id,
        promo_type,
        featured_flag,
        load_date,
        source_file,
        current_timestamp() as _dbt_loaded_at
    from source
    where campaign_id is not null
      and book_id is not null

)

select * from cleaned
