<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('routes', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->string('name');
            $table->date('route_date');
            $table->unsignedInteger('total_distance_m')->nullable();
            $table->unsignedInteger('total_duration_s')->nullable();
            $table->enum('status', ['draft', 'active', 'completed', 'cancelled'])->default('draft');
            $table->json('geometry')->nullable();
            $table->timestamps();

            $table->index(['user_id', 'route_date']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('routes');
    }
};
