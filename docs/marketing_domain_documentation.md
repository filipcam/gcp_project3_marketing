# Marketing Domain Documentation

## Overview

Domena Marketing odpowiada za:
- Zarządzanie kampaniami marketingowymi
- Przypisywanie kampanii do promowanych książek
- Pomiar dziennych metryk kampanii
- Publikowanie produktu danych pokazującego wpływ kampanii na sprzedaż

**Ważne**: Tabela `marketing_published_campaign_sales_attribution` jest **jedyną tabelą marketingową w folderze `shared`**. Pozostałe tabele (`marketing_campaigns.csv`, `marketing_campaign_products.csv`, `marketing_campaign_daily_metrics.csv`) są **własnością domeny Marketing** i znajdują się w folderze `marketing/`.

## Tabele marketingowe

### `marketing_campaigns.csv`

**Opis**: Tabela źródłowa opisująca kampanie marketingowe jako obiekty biznesowe.

| Kolumna | Typ | Opis |
|---|---|---|
| `campaign_id` | INT64 | Unikalny identyfikator kampanii |
| `campaign_name` | STRING | Nazwa kampanii (np. "Spring_Fantasy_Campaign_1") |
| `channel` | STRING | Kanał kampanii (Google Ads, Facebook Ads, Email, Instagram Ads, Affiliate) |
| `objective` | STRING | Cel kampanii (awareness, traffic, conversion, retention) |
| `target_segment` | STRING | Segment docelowy (new_customers, returning_customers, students, premium_readers, parents) |
| `start_date` | DATE | Data rozpoczęcia kampanii |
| `end_date` | DATE | Data zakończenia kampanii |
| `budget` | NUMERIC | Planowany budżet kampanii |
| `status` | STRING | Status kampanii (planned, active, finished) |
| `owner_team` | STRING | Zespół odpowiedzialny ("Marketing") |

---

### `marketing_campaign_products.csv`

**Opis**: Tabela mapująca kampanie na promowane książki z informacją o typie promocji.

| Kolumna | Typ | Opis |
|---|---|---|
| `campaign_product_id` | INT64 | Unikalny identyfikator rekordu kampania-produkt |
| `campaign_id` | INT64 | FK do `marketing_campaigns` |
| `book_id` | INT64 | FK do `catalog/books.csv` |
| `promo_type` | STRING | Typ promocji (discount, featured, homepage_banner, newsletter) |
| `discount_pct` | NUMERIC | Procent rabatu (0, 5, 10, 15, 20) |
| `featured_flag` | BOOL | Czy książka była wyróżniona jako główna kampanii |
| `promo_price` | NUMERIC | Cena promocyjna książki |
| `valid_from` | DATE | Okres obowiązywania promocji OD |
| `valid_to` | DATE | Okres obowiązywania promocji DO |

---

### `marketing_campaign_daily_metrics.csv`

**Opis**: Dzienne metryki performance'u kampanii z platform reklamowych.

| Kolumna | Typ | Opis |
|---|---|---|
| `campaign_id` | INT64 | FK do `marketing_campaigns` |
| `event_date` | DATE | Dzień pomiaru metryk |
| `impressions` | INT64 | Liczba wyświetleń reklamy/komunikatu |
| `clicks` | INT64 | Liczba kliknięć |
| `cost` | NUMERIC | Koszt kampanii w danym dniu |
| `sessions` | INT64 | Liczba sesji na stronie |
| `add_to_cart` | INT64 | Liczba dodania do koszyka |
| `conversions` | INT64 | Liczba konwersji marketingowych |
| `source_system` | STRING | Źródło danych (google_ads_platform, facebook_ads_platform, email) |

---

### `marketing_published_campaign_sales_attribution.csv` **(w folderze `shared/`)**

**Opis**: **Published data product** pokazujący wpływ kampanii na sprzedaż. Jedyna tabela marketingowa dostępna dla innych domen.

| Kolumna | Typ | Opis |
|---|---|---|
| `campaign_id` | INT64 | FK do `marketing_campaigns` |
| `book_id` | INT64 | FK do `catalog/books.csv` |
| `order_id` | INT64 | FK do `sales/orders.csv` |
| `order_item_id` | INT64 | FK do `sales/order_items.csv` |
| `order_date` | DATE | Data zamówienia |
| `customer_id` | INT64 | FK do `sales/orders.csv` |
| `quantity` | INT64 | Liczba sprzedanych sztuk (+/- dla zwrotów) |
| `unit_price` | NUMERIC | Cena jednostkowa sprzedaży |
| `line_amount` | NUMERIC | Wartość pozycji zamówienia |
| `attribution_type` | STRING | Typ przypisania (discount_match, featured_product, in_campaign_window) |
| `campaign_influence_score` | NUMERIC | Wskaźnik wpływu kampanii (v1=1.0) |
| `net_sales_amount` | NUMERIC | Wartość sprzedaży netto przypisana kampanii (+/- dla zwrotów) |
| `stock_available_at_campaign_snapshot` | INT64 | Dostępny stan magazynowy książki |

## Governance i ownership

| Tabela | Lokalizacja | Ownership | Typ danych |
|---|---|---|---|
| `marketing_campaigns.csv` | `marketing/` | Marketing (internal) | Źródłowe |
| `marketing_campaign_products.csv` | `marketing/` | Marketing (internal) | Źródłowe |
| `marketing_campaign_daily_metrics.csv` | `marketing/` | Marketing (internal) | Źródłowe |
| `marketing_published_campaign_sales_attribution.csv` | `shared/` | Marketing (published) | Produkt danych |

## Pytania do ustalenia z innymi domenami

### Z Sales
- Czy `order_status="returned"` odejmować od sprzedaży?
- Czy `customer_id` jest stabilnym kluczem między domenami?
- Czy `order_items.unit_price` to finalna cena sprzedaży?
- Czy marketing może korzystać z poziomu pojedynczego zamówienia, czy tylko z agregatów?

### Z Catalog
- Czy `book_id` jest oficjalnym i stabilnym kluczem produktu?
- Czy `list_price` jest źródłem prawdy dla ceny katalogowej?
- Czy kampanie mogą dotyczyć tylko książek, czy także kategorii?
- Czy kategorie i formaty są centralnie ustandaryzowane?

### Z Logistics
- Czy `stock_on_hand - stock_reserved` to właściwy sposób liczenia dostępności?
- Czy snapshot z jednej daty wystarcza do analiz marketingowych?
- Czy marketing powinien uwzględniać stockouty i problemy z dostępnością?
- Czy potrzebne są też dane o opóźnieniach dostaw?

### Z Architecture/Governance
- Czy `marketing_published_campaign_sales_attribution` pozostaje jedyną tabelą marketingową w `shared`?
- Jak wersjonujemy produkty danych?
- Czy kontrakty danych mają być w YAML/JSON?
- Jakie będą zasady IAM między domenami?

---

**Data Mesh status**: Domena Marketing publikuje jeden produkt danych w `shared/`. Pozostałe dane pozostają internal i są własnością domeny Marketing.
