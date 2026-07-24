<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class VisitLog extends Model
{
    use HasFactory;

    protected $fillable = [
        'user_id', 'doctor_id', 'pharmacy_id',
        'visited_at', 'duration_minutes', 'notes', 'outcome',
    ];

    protected $casts = [
        'visited_at' => 'datetime',
    ];

    public function representative()
    {
        return $this->belongsTo(User::class, 'user_id');
    }

    public function doctor()
    {
        return $this->belongsTo(Doctor::class);
    }

    public function pharmacy()
    {
        return $this->belongsTo(Pharmacy::class);
    }
}
