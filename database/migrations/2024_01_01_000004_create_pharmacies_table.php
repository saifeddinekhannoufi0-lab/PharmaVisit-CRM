<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('pharmacies', function (Blueprint $table) {
            $table->id();
            $table->foreignId('territory_id')->constrained()->cascadeOnDelete();
            $table->string('name');
            $table->string('address');
            $table->string('city');
            $table->string('postal_code', 10)->nullable();
            $table->string('region')->nullable();
            $table->decimal('lat', 10, 7)->nullable();
            $table->decimal('lng', 10, 7)->nullable();
            $table->timestamp('geocoded_at')->nullable();
            $table->string('phone', 20)->nullable();
            $table->string('manager_name')->nullable();
            $table->boolean('is_active')->default(true);
            $table->text('notes')->nullable();
            $table->timestamps();
            $table->softDeletes();

            $table->index(['territory_id', 'is_active']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('pharmacies');
    }
};
