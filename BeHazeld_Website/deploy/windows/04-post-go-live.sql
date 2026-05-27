-- ═══════════════════════════════════════════════════════════════════
--  BeHAZEL'd — Step 4: Post-Go-Live Security Hardening
--  Run this in SSMS AFTER confirming the site is live and working.
--  It revokes the DDL permissions Alembic needed during deployment.
-- ═══════════════════════════════════════════════════════════════════

USE [BeHAZELD];
GO

-- Revoke schema-level ALTER (no longer needed after migrations)
REVOKE ALTER ON SCHEMA::dbo FROM behazeld_app;
REVOKE CREATE TABLE          FROM behazeld_app;
REVOKE REFERENCES            FROM behazeld_app;
PRINT 'DDL permissions revoked from behazeld_app.';
GO

-- ── Verify final permission set ───────────────────────────────────────
SELECT
    dp.name       AS [Grantee],
    p.permission_name,
    p.state_desc  AS [State]
FROM   sys.database_permissions p
JOIN   sys.database_principals  dp ON p.grantee_principal_id = dp.principal_id
WHERE  dp.name = N'behazeld_app'
ORDER  BY p.permission_name;
GO

-- Expected result after this script:
--   CONNECT       GRANT
--   SELECT        GRANT  (via db_datareader role)
--   INSERT        GRANT  (via db_datawriter role)
--   UPDATE        GRANT  (via db_datawriter role)
--   DELETE        GRANT  (via db_datawriter role)
--
-- No CREATE TABLE, ALTER, or REFERENCES should appear.

PRINT '✅  Post-go-live hardening complete.';
