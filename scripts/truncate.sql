-- Delete all checkpoint data from all related tables
-- Order of deletion doesn't matter since there are no FK constraints
-- Using TRUNCATE for better performance when removing all data

BEGIN;

-- Truncate all checkpoint tables for optimal performance
-- TRUNCATE is much faster than DELETE for removing all rows
TRUNCATE TABLE public.checkpoint_writes;
TRUNCATE TABLE public.checkpoint_blobs;  
TRUNCATE TABLE public.checkpoints;

-- Reset any sequences if they exist (none found in current schema)
-- TRUNCATE automatically resets identity columns

COMMIT;