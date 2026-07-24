<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class Pharmacy extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'territory_id', 'name', 'address', 'city',
        'postal_code', 'region', 'lat', 'lng', 'geocoded_at',
        'phone', 'manager_name', 'is_active', 'notes',
    ];

    protected $casts = [
        'lat'         => 'float',
        'lng'         => 'float',
        'geocoded_at' => 'datetime',
        'is_active'   => 'boolean',
    ];

    public function getIsGeocodedAttribute(): bool
    {
        return $this->lat !== null && $this->lng !== null;
    }

    public function territory()
    {
        return $this->belongsTo(Territory::class);
    }

    public function visitLogs()
    {
        return $this->hasMany(VisitLog::class);
    }

    public function routeStops()
    {
        return $this->hasMany(RouteStop::class);
    }

    public function scopeActive($query)
    {
        return $query->where('is_active', true);
    }

    public function scopeInTerritory($query, int $territoryId)
    {
        return $query->where('territory_id', $territoryId);
    }
}
