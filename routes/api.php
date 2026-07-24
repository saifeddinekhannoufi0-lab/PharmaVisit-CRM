<?php

use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\DoctorController;
use App\Http\Controllers\Api\PharmacyController;
use App\Http\Controllers\Api\RouteController;
use App\Http\Controllers\Api\TerritoryController;
use App\Http\Controllers\Api\VisitLogController;
use Illuminate\Support\Facades\Route;

// ─── Public ───────────────────────────────────────────────────────────────────
Route::prefix('auth')->group(function () {
    Route::post('login', [AuthController::class, 'login'])->name('auth.login');
});

// ─── Protected (Sanctum token) ────────────────────────────────────────────────
Route::middleware('auth:sanctum')->group(function () {

    // Auth
    Route::prefix('auth')->group(function () {
        Route::post('logout', [AuthController::class, 'logout'])->name('auth.logout');
        Route::get('me',      [AuthController::class, 'me'])->name('auth.me');
    });

    // Territory
    Route::get('territory', [TerritoryController::class, 'show'])->name('territory.show');

    // Doctors & Pharmacies
    Route::apiResource('doctors',    DoctorController::class);
    Route::apiResource('pharmacies', PharmacyController::class);

    // Routes (optimization)
    Route::post('routes/optimize',                           [RouteController::class, 'optimize'])->name('routes.optimize');
    Route::get('routes',                                      [RouteController::class, 'index'])->name('routes.index');
    Route::get('routes/{route}',                              [RouteController::class, 'show'])->name('routes.show');
    Route::patch('routes/{route}/stops/{stop}/status',        [RouteController::class, 'updateStop'])->name('routes.stops.status');

    // Visit logs
    Route::get('visit-logs',  [VisitLogController::class, 'index'])->name('visit-logs.index');
    Route::post('visit-logs', [VisitLogController::class, 'store'])->name('visit-logs.store');
});
