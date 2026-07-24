<?php

namespace App\Console\Commands;

use App\Services\CacheService;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Cache;

class FlushPharmaCache extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'pharma:cache-flush
                            {--territory= : Flush caches for a specific territory ID}
                            {--routes     : Flush only route optimization caches}
                            {--all        : Flush everything (app + framework cache)}';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Flush PharmaVisit Redis caches (doctors, pharmacies, stats, routes)';

    /**
     * Execute the console command.
     */
    public function handle(): int
    {
        if ($this->option('all')) {
            Cache::flush();
            $this->components->info('🗑️  All caches flushed (app + framework).');
            return self::SUCCESS;
        }

        if ($territoryId = $this->option('territory')) {
            CacheService::invalidateTerritory((int) $territoryId);
            $this->components->info("🗑️  Flushed all caches for territory #{$territoryId} (doctors, pharmacies, stats).");
            return self::SUCCESS;
        }

        if ($this->option('routes')) {
            CacheService::invalidateAllRoutes();
            $this->components->info('🗑️  Flushed all route optimization caches.');
            return self::SUCCESS;
        }

        // Default: flush all PharmaVisit-specific caches
        CacheService::flushAll();
        $this->components->info('🗑️  Flushed all PharmaVisit caches (doctors, pharmacies, stats, routes).');

        return self::SUCCESS;
    }
}
