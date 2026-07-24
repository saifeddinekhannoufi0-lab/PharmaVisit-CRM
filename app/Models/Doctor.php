<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class Doctor extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'territory_id', 'first_name', 'last_name', 'specialty',
        'clinic_name', 'address', 'city', 'postal_code', 'region',
        'lat', 'lng', 'geocoded_at', 'phone', 'email',
        'priority', 'is_active', 'notes',
    ];

    protected $casts = [
        'lat'         => 'float',
        'lng'         => 'float',
        'geocoded_at' => 'datetime',
        'is_active'   => 'boolean',
    ];

    // ─── Accessors ────────────────────────────────────────────────────
    public function getFullNameAttribute(): string
    {
        return "Dr. {$this->first_name} {$this->last_name}";
    }

    public function getIsGeocodedAttribute(): bool
    {
        return $this->lat !== null && $this->lng !== null;
    }

    // ─── Relationships ────────────────────────────────────────────────
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

    // ─── Scopes ───────────────────────────────────────────────────────
    public function scopeActive($query)
    {
        return $query->where('is_active', true);
    }

    public function scopeInTerritory($query, int $territoryId)
    {
        return $query->where('territory_id', $territoryId);
    }

    public function scopeGeocoded($query)
    {
        return $query->whereNotNull('lat')->whereNotNull('lng');
    }
}
