<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('visit_logs', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->foreignId('doctor_id')->nullable()->constrained()->nullOnDelete();
            $table->foreignId('pharmacy_id')->nullable()->constrained()->nullOnDelete();
            $table->timestamp('visited_at');
            $table->unsignedSmallInteger('duration_minutes')->nullable();
            $table->text('notes')->nullable();
            $table->enum('outcome', ['completed', 'no_show', 'rescheduled', 'cancelled'])->default('completed');
            $table->timestamps();

            $table->index(['user_id', 'visited_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('visit_logs');
    }
};
