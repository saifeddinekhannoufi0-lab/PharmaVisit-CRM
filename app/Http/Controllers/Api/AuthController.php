<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\ValidationException;

class AuthController extends Controller
{
    /**
     * POST /api/auth/login
     * Returns a Sanctum bearer token for the rep.
     */
    public function login(Request $request): JsonResponse
    {
        $request->validate([
            'email'    => 'required|email',
            'password' => 'required|string',
        ]);

        $user = User::where('email', $request->email)
                    ->where('is_active', true)
                    ->first();

        if (! $user || ! Hash::check($request->password, $user->password)) {
            throw ValidationException::withMessages([
                'email' => ['The provided credentials are incorrect.'],
            ]);
        }

        // Revoke all previous tokens (single-session enforcement)
        $user->tokens()->delete();

        $token = $user->createToken('pharmavisit-rep')->plainTextToken;

        return response()->json([
            'token' => $token,
            'user'  => [
                'id'          => $user->id,
                'name'        => $user->name,
                'email'       => $user->email,
                'employee_id' => $user->employee_id,
                'territory'   => $user->territory?->only(['id', 'name', 'code', 'region']),
            ],
        ]);
    }

    /**
     * POST /api/auth/logout
     * Revokes the current bearer token.
     */
    public function logout(Request $request): JsonResponse
    {
        $request->user()->currentAccessToken()->delete();

        return response()->json(['message' => 'Logged out successfully.']);
    }

    /**
     * GET /api/auth/me
     * Returns the authenticated rep's profile.
     */
    public function me(Request $request): JsonResponse
    {
        $user = $request->user()->load('territory');

        return response()->json([
            'id'          => $user->id,
            'name'        => $user->name,
            'email'       => $user->email,
            'employee_id' => $user->employee_id,
            'phone'       => $user->phone,
            'territory'   => $user->territory?->only(['id', 'name', 'code', 'region']),
        ]);
    }
}
