-- db/seed_bulk_1000.sql
--
-- Generates 1,000 new demo bank customers (CUS-004 to CUS-1003) with accounts,
-- cards, and transactions, plus one year of extended history for the three
-- existing named users: bankinguser1@ktdemo.com (CUS-002),
-- bankinguser2@ktdemo.com (CUS-003), and kiran.thakkar@oracle.com.
--
-- Customer segments
--   CUS-004  to CUS-303   (300)  Premier tier
--   CUS-304  to CUS-1003  (700)  Standard tier
--
-- Account age
--   CUS-004  to CUS-403   (400)  Created ~5 years ago
--   CUS-404  to CUS-1003  (600)  Created ~2 years ago
--
-- Activity profile
--   CUS-004  to CUS-703   (700)  Active  – transactions spread over the past year
--   CUS-704  to CUS-1003  (300)  Dormant – last transaction 13-24 months ago
--
-- Account types
--   Premier  (004-303):  checking + savings + credit card
--   Active Standard (304-703): checking + savings; even-i also get credit card
--   Dormant Standard (704-1003): checking only; every 4th also gets savings
--
-- Run after seed.sql + seed_users_002_003.sql (does not touch CUS-001/002/003).

DECLARE
    TYPE str_tab IS TABLE OF VARCHAR2(60) INDEX BY PLS_INTEGER;

    v_first  str_tab;
    v_last   str_tab;

    v_cid     VARCHAR2(30);
    v_chk     VARCHAR2(30);
    v_sav     VARCHAR2(30);
    v_crd     VARCHAR2(30);
    v_card_d  VARCHAR2(30);
    v_card_c  VARCHAR2(30);

    v_tier    VARCHAR2(40);
    v_name    VARCHAR2(120);
    v_email   VARCHAR2(255);
    v_fn      VARCHAR2(60);
    v_ln      VARCHAR2(60);

    v_age     NUMBER;
    v_has_sav BOOLEAN;
    v_has_crd BOOLEAN;
    v_is_dorm BOOLEAN;

    v_chk_bal    NUMBER(14,2);
    v_sav_bal    NUMBER(14,2);
    v_crd_bal    NUMBER(14,2);
    v_crd_avail  NUMBER(14,2);
    v_crd_limit  NUMBER(14,2);
    v_sav_apr    NUMBER(6,2);

    v_r4      VARCHAR2(4);   -- routing last4
    v_a4_chk  VARCHAR2(4);   -- account last4 – checking
    v_a4_sav  VARCHAR2(4);   -- account last4 – savings
    v_a4_crd  VARCHAR2(4);   -- account last4 – credit

    v_base    NUMBER;
    v_amt     NUMBER(14,2);

    v_chk_acct  VARCHAR2(30);
    v_sav_acct  VARCHAR2(30);

BEGIN
    -- ── First names (30) ─────────────────────────────────────────
    v_first(1)  := 'James';       v_first(2)  := 'Mary';
    v_first(3)  := 'Robert';      v_first(4)  := 'Patricia';
    v_first(5)  := 'John';        v_first(6)  := 'Jennifer';
    v_first(7)  := 'Michael';     v_first(8)  := 'Linda';
    v_first(9)  := 'William';     v_first(10) := 'Barbara';
    v_first(11) := 'David';       v_first(12) := 'Elizabeth';
    v_first(13) := 'Richard';     v_first(14) := 'Susan';
    v_first(15) := 'Joseph';      v_first(16) := 'Jessica';
    v_first(17) := 'Thomas';      v_first(18) := 'Sarah';
    v_first(19) := 'Charles';     v_first(20) := 'Karen';
    v_first(21) := 'Christopher'; v_first(22) := 'Lisa';
    v_first(23) := 'Daniel';      v_first(24) := 'Nancy';
    v_first(25) := 'Matthew';     v_first(26) := 'Betty';
    v_first(27) := 'Anthony';     v_first(28) := 'Margaret';
    v_first(29) := 'Mark';        v_first(30) := 'Sandra';

    -- ── Last names (30) ──────────────────────────────────────────
    v_last(1)  := 'Smith';        v_last(2)  := 'Johnson';
    v_last(3)  := 'Williams';     v_last(4)  := 'Brown';
    v_last(5)  := 'Jones';        v_last(6)  := 'Garcia';
    v_last(7)  := 'Miller';       v_last(8)  := 'Davis';
    v_last(9)  := 'Rodriguez';    v_last(10) := 'Martinez';
    v_last(11) := 'Hernandez';    v_last(12) := 'Lopez';
    v_last(13) := 'Gonzalez';     v_last(14) := 'Wilson';
    v_last(15) := 'Anderson';     v_last(16) := 'Thomas';
    v_last(17) := 'Taylor';       v_last(18) := 'Moore';
    v_last(19) := 'Jackson';      v_last(20) := 'Martin';
    v_last(21) := 'Lee';          v_last(22) := 'Perez';
    v_last(23) := 'Thompson';     v_last(24) := 'White';
    v_last(25) := 'Harris';       v_last(26) := 'Sanchez';
    v_last(27) := 'Clark';        v_last(28) := 'Ramirez';
    v_last(29) := 'Lewis';        v_last(30) := 'Robinson';

    -- ═══════════════════════════════════════════════════════════════
    -- PART 1 : 1,000 new customers (CUS-004 … CUS-1003)
    -- ═══════════════════════════════════════════════════════════════
    FOR i IN 4..1003 LOOP

        v_cid    := 'CUS-'    || TO_CHAR(i);
        v_chk    := 'CHK-'    || TO_CHAR(i);
        v_sav    := 'SAV-'    || TO_CHAR(i);
        v_crd    := 'CRD-'    || TO_CHAR(i);
        v_card_d := 'CARD-D'  || TO_CHAR(i);
        v_card_c := 'CARD-C'  || TO_CHAR(i);

        -- Names: 30 × 30 = 900 unique combos, wrapping at 1,000
        v_fn   := v_first(MOD(i - 4, 30) + 1);
        v_ln   := v_last(MOD(FLOOR((i - 4) / 30), 30) + 1);
        v_name := v_fn || ' ' || v_ln;
        v_email := LOWER(v_fn) || '.' || LOWER(v_ln) || TO_CHAR(i) || '@demobank.example';

        -- Tier
        v_tier := CASE WHEN i <= 303 THEN 'Premier' ELSE 'Standard' END;

        -- Account age (days before today)
        v_age := CASE
                   WHEN i <= 403 THEN 1825 + MOD(i - 4,   90)   -- 5 yr ± 90 d
                   ELSE                730  + MOD(i - 404, 45)   -- 2 yr ± 45 d
                 END;

        -- Activity / dormancy flag
        v_is_dorm := (i >= 704);

        -- Which extra accounts exist
        v_has_sav := (i <= 303)
                  OR (i BETWEEN 304 AND 703)
                  OR (i >= 704 AND MOD(i, 4) = 0);   -- every 4th dormant gets savings

        v_has_crd := (i <= 303)
                  OR (i BETWEEN 304 AND 703 AND MOD(i, 2) = 0);

        -- Balances (deterministic)
        v_chk_bal   := ROUND(500  + MOD(i * 37,  9500), 2);
        v_sav_bal   := ROUND(1000 + MOD(i * 83, 49000), 2);
        v_crd_bal   := ROUND(MOD(i * 47, 4900), 2);
        v_crd_limit := CASE WHEN i <= 303 THEN 15000 ELSE 8000 END;
        v_crd_avail := v_crd_limit - v_crd_bal;
        v_sav_apr   := ROUND(3.50 + MOD(i, 15) * 0.10, 2);

        -- 4-digit strings for routing / account numbers
        v_r4     := LPAD(TO_CHAR(1000 + MOD(i * 11, 8999)), 4, '0');
        v_a4_chk := LPAD(TO_CHAR(1000 + MOD(i * 17, 8999)), 4, '0');
        v_a4_sav := LPAD(TO_CHAR(1000 + MOD(i * 23, 8999)), 4, '0');
        v_a4_crd := LPAD(TO_CHAR(1000 + MOD(i * 29, 8999)), 4, '0');

        -- ── Customer ─────────────────────────────────────────────
        INSERT INTO bank_customers (customer_id, full_name, email, tier, created_at)
        VALUES (v_cid, v_name, v_email, v_tier,
                CAST(TRUNC(SYSDATE) - v_age AS TIMESTAMP));

        -- ── Checking account ──────────────────────────────────────
        INSERT INTO bank_accounts (
            account_id, customer_id, account_name, account_type,
            balance, currency_code, routing_last4, account_last4, created_at
        ) VALUES (
            v_chk, v_cid,
            CASE MOD(i, 4)
                WHEN 0 THEN 'Primary Checking'
                WHEN 1 THEN 'Everyday Checking'
                WHEN 2 THEN 'Household Checking'
                ELSE        'Main Checking' END,
            'checking', v_chk_bal, 'USD', v_r4, v_a4_chk,
            CAST(TRUNC(SYSDATE) - v_age AS TIMESTAMP)
        );

        -- ── Debit card ────────────────────────────────────────────
        INSERT INTO bank_cards (
            card_id, customer_id, linked_account_id,
            card_name, network, last4, status, created_at
        ) VALUES (
            v_card_d, v_cid, v_chk, 'Debit Card',
            CASE MOD(i, 3) WHEN 0 THEN 'Visa' WHEN 1 THEN 'Mastercard' ELSE 'Visa Debit' END,
            v_a4_chk, 'active',
            CAST(TRUNC(SYSDATE) - v_age AS TIMESTAMP)
        );

        -- ── Savings account ───────────────────────────────────────
        IF v_has_sav THEN
            INSERT INTO bank_accounts (
                account_id, customer_id, account_name, account_type,
                balance, currency_code, routing_last4, account_last4, apr, created_at
            ) VALUES (
                v_sav, v_cid,
                CASE MOD(i, 3)
                    WHEN 0 THEN 'High-Yield Savings'
                    WHEN 1 THEN 'Emergency Savings'
                    ELSE        'Goal Saver' END,
                'savings', v_sav_bal, 'USD', v_r4, v_a4_sav, v_sav_apr,
                CAST(TRUNC(SYSDATE) - v_age AS TIMESTAMP)
            );
        END IF;

        -- ── Credit account + card ─────────────────────────────────
        IF v_has_crd THEN
            INSERT INTO bank_accounts (
                account_id, customer_id, account_name, account_type,
                balance, currency_code, account_last4, available_credit, created_at
            ) VALUES (
                v_crd, v_cid,
                CASE WHEN i <= 303 THEN 'Platinum Rewards Card' ELSE 'Cash Rewards Card' END,
                'credit', v_crd_bal, 'USD', v_a4_crd, v_crd_avail,
                CAST(TRUNC(SYSDATE) - v_age AS TIMESTAMP)
            );

            INSERT INTO bank_cards (
                card_id, customer_id, linked_account_id,
                card_name, network, last4, status, created_at
            ) VALUES (
                v_card_c, v_cid, v_crd,
                CASE WHEN i <= 303 THEN 'Platinum Rewards Card' ELSE 'Cash Rewards Card' END,
                CASE MOD(i, 2) WHEN 0 THEN 'Visa Signature' ELSE 'Mastercard World' END,
                v_a4_crd, 'active',
                CAST(TRUNC(SYSDATE) - v_age AS TIMESTAMP)
            );
        END IF;

        -- ══════════════════════════════════════════════════════════
        -- Transactions
        -- ══════════════════════════════════════════════════════════

        IF NOT v_is_dorm THEN
            -- ── ACTIVE: 12 months of monthly activity ─────────────
            FOR m IN 0..11 LOOP
                v_base := 5 + m * 30 + MOD(i + m, 5);

                -- Payroll (checking)
                INSERT INTO bank_transactions
                    (transaction_id, account_id, posted_on, description, amount, category)
                VALUES (
                    'txn-pay-' || TO_CHAR(i) || '-' || TO_CHAR(m),
                    v_chk, TRUNC(SYSDATE) - v_base,
                    'Payroll Deposit',
                    ROUND(2500 + MOD(i * 13, 3500), 2), 'income'
                );

                -- Utility (checking)
                INSERT INTO bank_transactions
                    (transaction_id, account_id, posted_on, description, amount, category)
                VALUES (
                    'txn-utl-' || TO_CHAR(i) || '-' || TO_CHAR(m),
                    v_chk, TRUNC(SYSDATE) - (v_base + 2),
                    CASE MOD(i + m, 4)
                        WHEN 0 THEN 'City Electric Co'
                        WHEN 1 THEN 'Metro Gas Service'
                        WHEN 2 THEN 'Water Authority'
                        ELSE        'Broadband Internet' END,
                    -(ROUND(55 + MOD(i * 3 + m, 145), 2)), 'utilities'
                );

                -- Groceries (checking)
                INSERT INTO bank_transactions
                    (transaction_id, account_id, posted_on, description, amount, category)
                VALUES (
                    'txn-groc-' || TO_CHAR(i) || '-' || TO_CHAR(m),
                    v_chk, TRUNC(SYSDATE) - (v_base + 7),
                    CASE MOD(i, 5)
                        WHEN 0 THEN 'Whole Foods Market'
                        WHEN 1 THEN 'Trader Joes'
                        WHEN 2 THEN 'Kroger'
                        WHEN 3 THEN 'Safeway'
                        ELSE        'Costco Wholesale' END,
                    -(ROUND(65 + MOD(i * 7 + m, 135), 2)), 'groceries'
                );

                -- Dining (checking, every other month)
                IF MOD(m, 2) = 0 THEN
                    INSERT INTO bank_transactions
                        (transaction_id, account_id, posted_on, description, amount, category)
                    VALUES (
                        'txn-din-' || TO_CHAR(i) || '-' || TO_CHAR(m),
                        v_chk, TRUNC(SYSDATE) - (v_base + 10),
                        CASE MOD(i + m, 4)
                            WHEN 0 THEN 'The Local Bistro'
                            WHEN 1 THEN 'Cheesecake Factory'
                            WHEN 2 THEN 'Olive Garden'
                            ELSE        'Chipotle Mexican Grill' END,
                        -(ROUND(20 + MOD(i * 9 + m, 80), 2)), 'dining'
                    );
                END IF;

                -- Savings transfer (if has savings)
                IF v_has_sav THEN
                    v_amt := ROUND(150 + MOD(i * 3, 350), 2);
                    INSERT INTO bank_transactions
                        (transaction_id, account_id, posted_on, description, amount, category)
                    VALUES (
                        'txn-tsf-' || TO_CHAR(i) || '-' || TO_CHAR(m),
                        v_chk, TRUNC(SYSDATE) - (v_base + 3),
                        'Transfer to Savings', -v_amt, 'transfer'
                    );

                    INSERT INTO bank_transactions
                        (transaction_id, account_id, posted_on, description, amount, category)
                    VALUES (
                        'txn-tsr-' || TO_CHAR(i) || '-' || TO_CHAR(m),
                        v_sav, TRUNC(SYSDATE) - (v_base + 3),
                        'Transfer from Checking', v_amt, 'transfer'
                    );

                    -- Monthly interest on savings
                    INSERT INTO bank_transactions
                        (transaction_id, account_id, posted_on, description, amount, category)
                    VALUES (
                        'txn-int-' || TO_CHAR(i) || '-' || TO_CHAR(m),
                        v_sav, TRUNC(SYSDATE) - (v_base + 25),
                        'Interest Credit',
                        ROUND(5 + MOD(i * 2 + m, 95), 2), 'interest'
                    );
                END IF;

                -- Credit card transactions (if has credit)
                IF v_has_crd THEN
                    INSERT INTO bank_transactions
                        (transaction_id, account_id, posted_on, description, amount, category)
                    VALUES (
                        'txn-crd1-' || TO_CHAR(i) || '-' || TO_CHAR(m),
                        v_crd, TRUNC(SYSDATE) - (v_base + 1),
                        CASE MOD(i + m, 6)
                            WHEN 0 THEN 'Amazon.com'
                            WHEN 1 THEN 'Netflix Subscription'
                            WHEN 2 THEN 'Shell Gas Station'
                            WHEN 3 THEN 'Target'
                            WHEN 4 THEN 'Starbucks'
                            ELSE        'Online Shopping' END,
                        ROUND(15 + MOD(i * 11 + m, 285), 2), 'shopping'
                    );

                    -- Second credit purchase (Premier only)
                    IF i <= 303 THEN
                        INSERT INTO bank_transactions
                            (transaction_id, account_id, posted_on, description, amount, category)
                        VALUES (
                            'txn-crd2-' || TO_CHAR(i) || '-' || TO_CHAR(m),
                            v_crd, TRUNC(SYSDATE) - (v_base + 12),
                            CASE MOD(i + m, 4)
                                WHEN 0 THEN 'SkyJet Airlines'
                                WHEN 1 THEN 'Marriott Hotels'
                                WHEN 2 THEN 'Luxury Spa'
                                ELSE        'Fine Dining' END,
                            ROUND(80 + MOD(i * 19 + m, 420), 2), 'travel'
                        );
                    END IF;

                    -- Monthly credit payment
                    INSERT INTO bank_transactions
                        (transaction_id, account_id, posted_on, description, amount, category)
                    VALUES (
                        'txn-cpay-' || TO_CHAR(i) || '-' || TO_CHAR(m),
                        v_crd, TRUNC(SYSDATE) - (v_base + 16),
                        'Payment Received',
                        -(ROUND(100 + MOD(i * 5 + m, 400), 2)), 'payment'
                    );
                END IF;

            END LOOP;  -- end month loop (active)

        ELSE
            -- ── DORMANT: 5 transactions, all 13-24 months ago ──────
            FOR m IN 0..4 LOOP
                v_base := 400 + m * 25 + MOD(i, 30);  -- 400–530 days ago

                INSERT INTO bank_transactions
                    (transaction_id, account_id, posted_on, description, amount, category)
                VALUES (
                    'txn-dmt-' || TO_CHAR(i) || '-' || TO_CHAR(m),
                    v_chk, TRUNC(SYSDATE) - v_base,
                    CASE MOD(m, 5)
                        WHEN 0 THEN 'Payroll Deposit'
                        WHEN 1 THEN 'Rent Payment'
                        WHEN 2 THEN 'Grocery Store'
                        WHEN 3 THEN 'Gas Station'
                        ELSE        'Utilities Bill' END,
                    CASE MOD(m, 5)
                        WHEN 0 THEN  ROUND(1800 + MOD(i,       2200), 2)
                        WHEN 1 THEN -(ROUND( 800 + MOD(i,       1200), 2))
                        WHEN 2 THEN -(ROUND(  45 + MOD(i,        120), 2))
                        WHEN 3 THEN -(ROUND(  35 + MOD(i,         55), 2))
                        ELSE        -(ROUND(  60 + MOD(i * 3,    140), 2)) END,
                    CASE MOD(m, 5)
                        WHEN 0 THEN 'income'
                        WHEN 1 THEN 'housing'
                        WHEN 2 THEN 'groceries'
                        WHEN 3 THEN 'transportation'
                        ELSE        'utilities' END
                );
            END LOOP;

            -- Dormant savings interest (for the ~25% who have savings)
            IF v_has_sav THEN
                INSERT INTO bank_transactions
                    (transaction_id, account_id, posted_on, description, amount, category)
                VALUES (
                    'txn-dmt-si-' || TO_CHAR(i),
                    v_sav, TRUNC(SYSDATE) - (400 + MOD(i, 60)),
                    'Interest Credit',
                    ROUND(8 + MOD(i, 42), 2), 'interest'
                );
            END IF;

        END IF;  -- end active / dormant branch

    END LOOP;  -- end customer loop

    -- ═══════════════════════════════════════════════════════════════
    -- PART 2 : Extended history for CUS-002 (bankinguser1@ktdemo.com)
    --           Adds Apr 2025 – Feb 2026  (m = 2..12 months before today)
    -- ═══════════════════════════════════════════════════════════════
    FOR m IN 2..12 LOOP
        v_base := m * 30 + 15;

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h002-pay-'  || TO_CHAR(m), 'CHK-002',
                TRUNC(SYSDATE) - v_base,
                'Payroll Deposit', 4100.00, 'income');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h002-utl-'  || TO_CHAR(m), 'CHK-002',
                TRUNC(SYSDATE) - (v_base + 3),
                CASE MOD(m, 4) WHEN 0 THEN 'City Electric Co'
                               WHEN 1 THEN 'Metro Gas Service'
                               WHEN 2 THEN 'Water Authority'
                               ELSE        'Broadband Internet' END,
                -(79 + MOD(m * 7, 100)), 'utilities');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h002-groc-' || TO_CHAR(m), 'CHK-002',
                TRUNC(SYSDATE) - (v_base + 7),
                CASE MOD(m, 3) WHEN 0 THEN 'Whole Foods Market'
                               WHEN 1 THEN 'Costco Wholesale'
                               ELSE        'Northside Grocery' END,
                -(120 + MOD(m * 11, 80)), 'groceries');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h002-tsf-'  || TO_CHAR(m), 'CHK-002',
                TRUNC(SYSDATE) - (v_base + 5),
                'Transfer to Savings', -750.00, 'transfer');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h002-tsr-'  || TO_CHAR(m), 'SAV-002',
                TRUNC(SYSDATE) - (v_base + 5),
                'Transfer from Checking', 750.00, 'transfer');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h002-int-'  || TO_CHAR(m), 'SAV-002',
                TRUNC(SYSDATE) - (v_base + 27),
                'Interest Credit', ROUND(55 + MOD(m, 20), 2), 'interest');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h002-crd-'  || TO_CHAR(m), 'CRD-002',
                TRUNC(SYSDATE) - (v_base + 2),
                CASE MOD(m, 4) WHEN 0 THEN 'Amazon.com'
                               WHEN 1 THEN 'Downtown Bistro'
                               WHEN 2 THEN 'Shell Gas Station'
                               ELSE        'Target' END,
                ROUND(35 + MOD(m * 13, 215), 2), 'shopping');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h002-cpay-' || TO_CHAR(m), 'CRD-002',
                TRUNC(SYSDATE) - (v_base + 15),
                'Payment Received', -225.00, 'payment');
    END LOOP;

    -- ═══════════════════════════════════════════════════════════════
    -- PART 3 : Extended history for CUS-003 (bankinguser2@ktdemo.com)
    -- ═══════════════════════════════════════════════════════════════
    FOR m IN 2..12 LOOP
        v_base := m * 30 + 15;

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h003-pay-'  || TO_CHAR(m), 'CHK-003',
                TRUNC(SYSDATE) - v_base,
                'Mobile Deposit', 1800.00, 'income');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h003-utl-'  || TO_CHAR(m), 'CHK-003',
                TRUNC(SYSDATE) - (v_base + 4),
                CASE MOD(m, 3) WHEN 0 THEN 'Water Utility'
                               WHEN 1 THEN 'City Electric Co'
                               ELSE        'Gas Service' END,
                -(48 + MOD(m * 5, 62)), 'utilities');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h003-groc-' || TO_CHAR(m), 'CHK-003',
                TRUNC(SYSDATE) - (v_base + 6),
                CASE MOD(m, 2) WHEN 0 THEN 'Kroger' ELSE 'Safeway' END,
                -(85 + MOD(m * 9, 65)), 'groceries');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h003-tsf-'  || TO_CHAR(m), 'CHK-003',
                TRUNC(SYSDATE) - (v_base + 5),
                'Transfer to Savings', -300.00, 'transfer');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h003-tsr-'  || TO_CHAR(m), 'SAV-003',
                TRUNC(SYSDATE) - (v_base + 5),
                'Transfer from Checking', 300.00, 'transfer');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h003-int-'  || TO_CHAR(m), 'SAV-003',
                TRUNC(SYSDATE) - (v_base + 27),
                'Interest Credit', ROUND(25 + MOD(m, 15), 2), 'interest');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h003-crd-'  || TO_CHAR(m), 'CRD-003',
                TRUNC(SYSDATE) - (v_base + 3),
                CASE MOD(m, 4) WHEN 0 THEN 'Metro Electronics'
                               WHEN 1 THEN 'Green Garden Cafe'
                               WHEN 2 THEN 'Community Pharmacy'
                               ELSE        'Online Shopping' END,
                ROUND(25 + MOD(m * 17, 225), 2), 'shopping');

        INSERT INTO bank_transactions
            (transaction_id, account_id, posted_on, description, amount, category)
        VALUES ('txn-h003-cpay-' || TO_CHAR(m), 'CRD-003',
                TRUNC(SYSDATE) - (v_base + 15),
                'Payment Received', -300.00, 'payment');
    END LOOP;

    -- ═══════════════════════════════════════════════════════════════
    -- PART 4 : Extended history for kiran.thakkar@oracle.com
    --           Resolved dynamically via email lookup
    -- ═══════════════════════════════════════════════════════════════
    BEGIN
        SELECT a.account_id INTO v_chk_acct
        FROM   bank_accounts  a
        JOIN   bank_customers c ON a.customer_id = c.customer_id
        WHERE  LOWER(c.email) = 'kiran.thakkar@oracle.com'
          AND  a.account_type = 'checking'
        FETCH FIRST 1 ROW ONLY;

        FOR m IN 2..12 LOOP
            v_base := m * 30 + 15;

            INSERT INTO bank_transactions
                (transaction_id, account_id, posted_on, description, amount, category)
            VALUES ('txn-hkt-pay-'  || TO_CHAR(m), v_chk_acct,
                    TRUNC(SYSDATE) - v_base,
                    'Payroll Deposit', 5500.00, 'income');

            INSERT INTO bank_transactions
                (transaction_id, account_id, posted_on, description, amount, category)
            VALUES ('txn-hkt-utl-'  || TO_CHAR(m), v_chk_acct,
                    TRUNC(SYSDATE) - (v_base + 3),
                    CASE MOD(m, 3) WHEN 0 THEN 'City Electric Co'
                                   WHEN 1 THEN 'Water Services'
                                   ELSE        'Broadband Internet' END,
                    -(90 + MOD(m * 7, 110)), 'utilities');

            INSERT INTO bank_transactions
                (transaction_id, account_id, posted_on, description, amount, category)
            VALUES ('txn-hkt-groc-' || TO_CHAR(m), v_chk_acct,
                    TRUNC(SYSDATE) - (v_base + 6),
                    CASE MOD(m, 3) WHEN 0 THEN 'Whole Foods Market'
                                   WHEN 1 THEN 'Costco Wholesale'
                                   ELSE        'Trader Joes' END,
                    -(130 + MOD(m * 11, 120)), 'groceries');

            INSERT INTO bank_transactions
                (transaction_id, account_id, posted_on, description, amount, category)
            VALUES ('txn-hkt-din-'  || TO_CHAR(m), v_chk_acct,
                    TRUNC(SYSDATE) - (v_base + 9),
                    CASE MOD(m, 3) WHEN 0 THEN 'Fine Dining Restaurant'
                                   WHEN 1 THEN 'Business Lunch'
                                   ELSE        'Sushi Bar' END,
                    -(85 + MOD(m * 13, 165)), 'dining');
        END LOOP;

        -- Savings account for kiran (if one exists)
        BEGIN
            SELECT a.account_id INTO v_sav_acct
            FROM   bank_accounts  a
            JOIN   bank_customers c ON a.customer_id = c.customer_id
            WHERE  LOWER(c.email) = 'kiran.thakkar@oracle.com'
              AND  a.account_type = 'savings'
            FETCH FIRST 1 ROW ONLY;

            FOR m IN 2..12 LOOP
                v_base := m * 30 + 15;

                INSERT INTO bank_transactions
                    (transaction_id, account_id, posted_on, description, amount, category)
                VALUES ('txn-hkt-tsf-' || TO_CHAR(m), v_chk_acct,
                        TRUNC(SYSDATE) - (v_base + 4),
                        'Transfer to Savings', -1000.00, 'transfer');

                INSERT INTO bank_transactions
                    (transaction_id, account_id, posted_on, description, amount, category)
                VALUES ('txn-hkt-tsr-' || TO_CHAR(m), v_sav_acct,
                        TRUNC(SYSDATE) - (v_base + 4),
                        'Transfer from Checking', 1000.00, 'transfer');

                INSERT INTO bank_transactions
                    (transaction_id, account_id, posted_on, description, amount, category)
                VALUES ('txn-hkt-int-' || TO_CHAR(m), v_sav_acct,
                        TRUNC(SYSDATE) - (v_base + 26),
                        'Interest Credit', ROUND(75 + MOD(m * 3, 45), 2), 'interest');
            END LOOP;
        EXCEPTION
            WHEN NO_DATA_FOUND THEN NULL;  -- No savings account; skip silently
        END;

    EXCEPTION
        WHEN NO_DATA_FOUND THEN NULL;  -- kiran not in banking DB; skip silently
    END;

    COMMIT;
    DBMS_OUTPUT.PUT_LINE('seed_bulk_1000.sql completed successfully.');

END;
/
