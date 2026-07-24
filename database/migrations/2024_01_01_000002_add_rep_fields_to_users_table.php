<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->string('employee_id')->unique()->nullable()->after('id');
            $table->foreignId('territory_id')->nullable()->constrained()->nullOnDelete()->after('employee_id');
            $table->string('phone', 20)->nullable()->after('email');
            $table->boolean('is_active')->default(true)->after('phone');
        });
    }

    public function down(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->dropForeign(['territory_id']);
            $table->dropColumn(['employee_id', 'territory_id', 'phone', 'is_active']);
        });
    }
};
