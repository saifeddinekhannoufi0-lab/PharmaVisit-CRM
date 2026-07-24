<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class RouteStop extends Model
{
    use HasFactory;

    protected $fillable = [
        'route_id', 'stop_order', 'doctor_id', 'pharmacy_id',
        'arrival_time', 'departure_time', 'status', 'notes',
    ];

    public function route()
    {
        return $this->belongsTo(Route::class);
    }

    public function doctor()
    {
        return $this->belongsTo(Doctor::class);
    }

    public function pharmacy()
    {
        return $this->belongsTo(Pharmacy::class);
    }

    /**
     * Get the target entity (doctor or pharmacy) regardless of which one it is.
     */
    public function getTargetAttribute(): Doctor|Pharmacy|null
    {
        return $this->doctor ?? $this->pharmacy;
    }
}
