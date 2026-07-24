<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Territory extends Model
{
    use HasFactory;

    protected $fillable = ['name', 'code', 'region', 'description'];

    public function representatives()
    {
        return $this->hasMany(User::class);
    }

    public function doctors()
    {
        return $this->hasMany(Doctor::class);
    }

    public function pharmacies()
    {
        return $this->hasMany(Pharmacy::class);
    }
}
