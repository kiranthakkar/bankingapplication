DELETE FROM bank_transactions;
DELETE FROM bank_cards;
DELETE FROM bank_accounts;
DELETE FROM bank_customers;

INSERT INTO bank_customers (customer_id, identity_subject, full_name, email, tier)
VALUES ('CUS-001', 'demo-user', 'Jordan Lee', 'jordan.lee@examplebank.demo', 'Premier');

INSERT INTO bank_accounts (
    account_id, customer_id, account_name, account_type, balance, currency_code, routing_last4, account_last4
) VALUES (
    'CHK-001', 'CUS-001', 'Everyday Checking', 'checking', 4825.17, 'USD', '1107', '2048'
);

INSERT INTO bank_accounts (
    account_id, customer_id, account_name, account_type, balance, currency_code, routing_last4, account_last4, apr
) VALUES (
    'SAV-001', 'CUS-001', 'Rainy Day Savings', 'savings', 12540.80, 'USD', '1107', '7711', 4.15
);

INSERT INTO bank_accounts (
    account_id, customer_id, account_name, account_type, balance, currency_code, account_last4, available_credit
) VALUES (
    'CRD-001', 'CUS-001', 'Travel Rewards Card', 'credit', 642.18, 'USD', '9184', 7357.82
);

INSERT INTO bank_cards (
    card_id, customer_id, linked_account_id, card_name, network, last4, status
) VALUES (
    'CARD-001', 'CUS-001', 'CHK-001', 'Debit Card', 'Visa', '4832', 'active'
);

INSERT INTO bank_cards (
    card_id, customer_id, linked_account_id, card_name, network, last4, status
) VALUES (
    'CARD-002', 'CUS-001', 'CRD-001', 'Travel Rewards Card', 'Visa Signature', '9184', 'active'
);

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-1001', 'CHK-001', TRUNC(SYSDATE) - 1, 'Payroll Deposit', 3200.00, 'income');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-1002', 'CHK-001', TRUNC(SYSDATE) - 2, 'City Power Utility', -124.33, 'utilities');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-1003', 'CHK-001', TRUNC(SYSDATE) - 4, 'Farmers Market', -63.42, 'groceries');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-1004', 'CHK-001', TRUNC(SYSDATE) - 6, 'Transfer to Savings', -500.00, 'transfer');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-2001', 'SAV-001', TRUNC(SYSDATE) - 6, 'Transfer from Checking', 500.00, 'transfer');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-2002', 'SAV-001', TRUNC(SYSDATE) - 25, 'Interest Credit', 38.77, 'interest');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-3001', 'CRD-001', TRUNC(SYSDATE) - 1, 'SkyJet Airlines', 318.94, 'travel');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-3002', 'CRD-001', TRUNC(SYSDATE) - 3, 'Blue Bottle Coffee', 14.25, 'dining');

INSERT INTO bank_transactions (transaction_id, account_id, posted_on, description, amount, category)
VALUES ('txn-3003', 'CRD-001', TRUNC(SYSDATE) - 8, 'Payment Received', -250.00, 'payment');

COMMIT;
