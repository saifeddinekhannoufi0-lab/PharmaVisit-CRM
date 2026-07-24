<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\VisitLog;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class VisitLogController extends Controller
{
    /**
     * POST /api/visit-logs
     * Log a visit to a doctor or pharmacy.
     */
    public function store(Request $request): JsonResponse
    {
        $data = $request->validate([
            'doctor_id'       => 'nullable|integer|exists:doctors,id',
            'pharmacy_id'     => 'nullable|integer|exists:pharmacies,id',
            'notes'           => 'nullable|string',
            'duration_minutes'=> 'nullable|integer|min:1|max:480',
            'outcome'         => 'required|in:completed,no_show,rescheduled,cancelled',
            'visited_at'      => 'nullable|date',
        ]);

        if (empty($data['doctor_id']) && empty($data['pharmacy_id'])) {
            return response()->json([
                'message' => 'Either doctor_id or pharmacy_id is required.',
            ], 422);
        }

        $log = VisitLog::create([
            'user_id'          => $request->user()->id,
            'doctor_id'        => $data['doctor_id'] ?? null,
            'pharmacy_id'      => $data['pharmacy_id'] ?? null,
            'notes'            => $data['notes'] ?? null,
            'duration_minutes' => $data['duration_minutes'] ?? null,
            'outcome'          => $data['outcome'],
            'visited_at'       => $data['visited_at'] ?? now(),
        ]);

        $log->load(['doctor:id,first_name,last_name,specialty', 'pharmacy:id,name']);

        return response()->json($log, 201);
    }

    /**
     * GET /api/visit-logs
     * My recent visit history.
     */
    public function index(Request $request): JsonResponse
    {
        $logs = VisitLog::where('user_id', $request->user()->id)
            ->with([
                'doctor:id,first_name,last_name,specialty,city',
                'pharmacy:id,name,city',
            ])
            ->orderByDesc('visited_at')
            ->paginate(30);

        return response()->json($logs);
    }
}
