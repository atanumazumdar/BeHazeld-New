-- ═══════════════════════════════════════════════════════════════════
--  BeHAZEL'd — Step 2: MS SQL Server Database Setup
--  Run this in SSMS connected as SA or sysadmin.
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. Create the application database ───────────────────────────────
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'BeHAZELD')
BEGIN
    CREATE DATABASE BeHAZELD
        COLLATE SQL_Latin1_General_CP1_CI_AS;
    PRINT 'Database BeHAZELD created.';
END
ELSE
    PRINT 'Database BeHAZELD already exists — skipping creation.';
GO

-- ── 2. Create the application login ──────────────────────────────────
-- ⚠  Replace <YourStrongPassword> with a real password before running!
USE [master];
GO

IF NOT EXISTS (SELECT name FROM sys.server_principals WHERE name = N'behazeld_app')
BEGIN
    CREATE LOGIN behazeld_app
        WITH PASSWORD        = N'<YourStrongPassword>',
             CHECK_POLICY    = ON,
             CHECK_EXPIRATION = OFF;
    PRINT 'Login behazeld_app created.';
END
ELSE
    PRINT 'Login behazeld_app already exists — skipping.';
GO

-- ── 3. Map login to database user + grant permissions ─────────────────
USE [BeHAZELD];
GO

IF NOT EXISTS (SELECT name FROM sys.database_principals WHERE name = N'behazeld_app')
BEGIN
    CREATE USER behazeld_app FOR LOGIN behazeld_app;
    PRINT 'Database user behazeld_app created.';
END
GO

-- Read + write access for the application
ALTER ROLE db_datareader ADD MEMBER behazeld_app;
ALTER ROLE db_datawriter ADD MEMBER behazeld_app;

-- DDL rights needed by Alembic to create/alter tables.
-- These CAN be revoked after the first successful `alembic upgrade head`.
GRANT CREATE TABLE  TO behazeld_app;
GRANT ALTER ON SCHEMA::dbo TO behazeld_app;
GRANT REFERENCES    TO behazeld_app;
PRINT 'Permissions granted to behazeld_app.';
GO

-- ── 4. Enable SQL Server TCP/IP (run in SSMS if needed) ──────────────
-- This block uses xp_cmdshell to enable TCP/IP via sqlservermanager.
-- Alternatively, enable via SQL Server Configuration Manager GUI.
--
-- EXEC sp_configure 'show advanced options', 1; RECONFIGURE;
-- EXEC sp_configure 'xp_cmdshell', 1; RECONFIGURE;
-- EXEC xp_cmdshell 'powershell.exe -Command "& {
--     $smo = (new-object Microsoft.SqlServer.Management.Smo.Wmi.ManagedComputer);
--     $tcp = $smo.ServerInstances[''MSSQLSERVER''].ServerProtocols[''Tcp''];
--     $tcp.IsEnabled = $true; $tcp.Alter()
-- }"';

-- ── 5. Verify ─────────────────────────────────────────────────────────
SELECT
    dp.name        AS [DatabaseUser],
    sp.name        AS [ServerLogin],
    dp.type_desc   AS [PrincipalType],
    dp.create_date AS [Created]
FROM   sys.database_principals dp
LEFT   JOIN sys.server_principals sp ON dp.sid = sp.sid
WHERE  dp.name = N'behazeld_app';
GO

PRINT '✅  SQL Server setup complete.  Run alembic upgrade head next.';
