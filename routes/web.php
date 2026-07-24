<?php

use App\Http\Controllers\DashboardController;
use Illuminate\Support\Facades\Route;

Route::get('/', fn() => redirect('/dashboard'));
Route::get('/dashboard', [DashboardController::class, 'index'])->name('dashboard');
Route::get('/login', fn() => view('app'))->name('login');
// All other routes → SPA handles routing client-side
Route::get('/{any}', [DashboardController::class, 'index'])->where('any', '.*');
