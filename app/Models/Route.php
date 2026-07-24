<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Route extends Model
{
    use HasFactory;

    protected $fillable = [
        'user_id', 'name', 'route_date',
        'total_distance_m', 'total_duration_s',
        'status', 'geometry',
    ];

    protected $casts = [
        'route_date' => 'date',
        'geometry'   => 'array',
    ];

    public function representative()
    {
        return $this->belongsTo(User::class, 'user_id');
    }

    public function stops()
    {
        return $this->hasMany(RouteStop::class)->orderBy('stop_order');
    }
}
