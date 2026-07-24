<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('route_stops', function (Blueprint $table) {
            $table->id();
            $table->foreignId('route_id')->constrained()->cascadeOnDelete();
            $table->unsignedTinyInteger('stop_order');
            $table->foreignId('doctor_id')->nullable()->constrained()->nullOnDelete();
            $table->foreignId('pharmacy_id')->nullable()->constrained()->nullOnDelete();
            $table->time('arrival_time')->nullable();
            $table->time('departure_time')->nullable();
            $table->enum('status', ['pending', 'visited', 'skipped'])->default('pending');
            $table->text('notes')->nullable();
            $table->timestamps();

            $table->index(['route_id', 'stop_order']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('route_stops');
    }
};
