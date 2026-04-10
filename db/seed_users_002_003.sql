-- Incremental seed data for OCI Identity Domain users:
--   CUS-002 -> bankinguser1@ktdemo.com
--   CUS-003 -> bankinguser2@ktdemo.com
--
-- Run this after db/seed.sql to add two more demo customers without
-- clearing the existing sample data.

DELETE FROM bank_transactions
WHERE account_id IN (
    'CHK-002', 'SAV-002', 'CRD-002',
    'CHK-003', 'SAV-003', 'CRD-003'
);

DELETE FROM bank_cards
WHERE customer_id IN ('CUS-002', 'CUS-003')
   OR linked_account_id IN (
       'CHK-002', 'CRD-002',
       'CHK-003', 'CRD-003'
   );

DELETE FROM bank_accounts
WHERE customer_id IN ('CUS-002', 'CUS-003');

DELETE FROM bank_customers
WHERE customer_id IN ('CUS-002', 'CUS-003');

INSERT INTO bank_customers (customer_id, identity_subject, full_name, email, tier)
VALUES ('CUS-002', 'bankinguser1@ktdemo.com', 'Banking User1', 'bankinguser1@ktdemo.com', 'Premier');

INSERT INTO bank_customers (customer_id, identity_subject, full_name, email, tier)
VALUES ('CUS-003', 'bankinguser2@ktdemo.com', 'Banking User2', 'bankinguser2@ktdemo.com', 'Standard');

INSERT INTO bank_accounts (
    account_id, customer_id, account_name, account_type, balance, currency_code, routing_last4, account_last4
) VALUES (
    'CHK-002', 'CUS-002', 'Primary Checking', 'checking', 6310.44, 'USD', '1107', '2201'
);

INSERT INTO bank_accounts (
    account_id, customer_id, account_name, account_type, balance, currency_code, routing_last4, account_last4, apr
) VALUES (
    'SAV-002', 'CUS-002', 'Emergency Savings', 'savings', 18250.00, 'USD', '1107', '8802', 4.10
);

INSERT INTO bank_accounts (
    account_id, customer_id, account_name, account_type, balance, currency_code, account_last4, available_credit
) VALUES (
    'CRD-002', 'CUS-002', 'Cash Rewards Card', 'credit', 428.90, 'USD', '4403', 9571.10
);

INSERT INTO bank_accounts (
    account_id, customer_id, account_name, account_type, balance, currency_code, routing_last4, account_last4
) VALUES (
    'CHK-003', 'CUS-003', 'Household Checking', 'checking', 2740.63, 'USD', '1107', '3304'
);

INSERT INTO bank_accounts (
    account_id, customer_id, account_name, account_type, balance, currency_code, routing_last4, account_last4, apr
) VALUES (
    'SAV-003', 'CUS-003', 'Goal Saver', 'savings', 9540.25, 'USD', '1107', '9905', 3.95
);

INSERT INTO bank_accounts (
    account_id, customer_id, account_name, account_type, balance, currency_code, account_last4, available_credit
) VALUES (
    'CRD-003', 'CUS-003', 'Everyday Credit Card', 'credit', 1189.47, 'USD', '5506', 6810.53
);

INSERT INTO bank_cards (
    card_id, customer_id, linked_account_id, card_name, network, last4, status
) VALUES (
    'CARD-003', 'CUS-002', 'CHK-002', 'Debit Card', 'Visa', '2201', 'active'
);

INSERT INTO bank_cards (
    card_id, customer_id, linked_account_id, card_name, network, last4, status
) VALUES (
    'CARD-004', 'CUS-002', 'CRD-002', 'Cash Rewards Card', 'Visa Signature', '4403', 'active'
);

INSERT INTO bank_cards (
    card_id, customer_id, linked_account_id, card_name, network, last4, status
) VALUES (
    'CARD-005', 'CUS-003', 'CHK-003', 'Debit Card', 'Mastercard', '3304', 'active'
);

INSERT INTO bank_cards (
    card_id, customer_id, linked_account_id, card_name, network, last4, status
) VALUES (
    'CARD-006', 'CUS-003', 'CRD-003', 'Everyday Credit Card', 'Mastercard World', '5506', 'active'
);

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-4001', 'CHK-002', TRUNC(SYSDATE) - 1, 'Payroll Deposit', 4100.00, 'income');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-4002', 'CHK-002', TRUNC(SYSDATE) - 2, 'Northside Grocery', -142.18, 'groceries');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-4003', 'CHK-002', TRUNC(SYSDATE) - 4, 'Transfer to Savings', -750.00, 'transfer');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-4004', 'CHK-002', TRUNC(SYSDATE) - 6, 'Internet Service Provider', -79.99, 'utilities');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-5001', 'SAV-002', TRUNC(SYSDATE) - 4, 'Transfer from Checking', 750.00, 'transfer');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-5002', 'SAV-002', TRUNC(SYSDATE) - 28, 'Interest Credit', 61.83, 'interest');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-6001', 'CRD-002', TRUNC(SYSDATE) - 1, 'Downtown Bistro', 58.42, 'dining');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-6002', 'CRD-002', TRUNC(SYSDATE) - 5, 'Fuel Express', 47.16, 'transportation');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-6003', 'CRD-002', TRUNC(SYSDATE) - 9, 'Payment Received', -225.00, 'payment');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-7001', 'CHK-003', TRUNC(SYSDATE) - 1, 'Mobile Deposit', 1200.00, 'income');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-7002', 'CHK-003', TRUNC(SYSDATE) - 3, 'Community Pharmacy', -26.73, 'health');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-7003', 'CHK-003', TRUNC(SYSDATE) - 5, 'Transfer to Savings', -300.00, 'transfer');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-7004', 'CHK-003', TRUNC(SYSDATE) - 8, 'Water Utility', -48.29, 'utilities');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-8001', 'SAV-003', TRUNC(SYSDATE) - 5, 'Transfer from Checking', 300.00, 'transfer');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-8002', 'SAV-003', TRUNC(SYSDATE) - 30, 'Interest Credit', 29.54, 'interest');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-9001', 'CRD-003', TRUNC(SYSDATE) - 2, 'Metro Electronics', 249.99, 'shopping');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-9002', 'CRD-003', TRUNC(SYSDATE) - 6, 'Green Garden Cafe', 32.18, 'dining');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-9003', 'CRD-003', TRUNC(SYSDATE) - 10, 'Payment Received', -300.00, 'payment');

COMMIT;
