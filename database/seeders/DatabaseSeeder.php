<?php

namespace Database\Seeders;

use App\Models\Territory;
use App\Models\User;
use App\Models\Doctor;
use App\Models\Pharmacy;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        // ─── Territories ──────────────────────────────────────────────
        $rabat = Territory::create([
            'name'        => 'Grand Rabat',
            'code'        => 'MAR-RAB',
            'region'      => 'Rabat-Salé-Kénitra',
            'description' => 'Rabat, Salé, Témara and surroundings',
        ]);

        $casa = Territory::create([
            'name'        => 'Casablanca Nord',
            'code'        => 'MAR-CAS',
            'region'      => 'Casablanca-Settat',
            'description' => 'Northern Casablanca districts',
        ]);

        // ─── Representatives ──────────────────────────────────────────
        $sarah = User::create([
            'name'        => 'Sarah Bennani',
            'email'       => 'sarah@pharmavisit.ma',
            'password'    => Hash::make('password'),
            'employee_id' => 'REP-001',
            'territory_id'=> $rabat->id,
            'phone'       => '+212 6 12 34 56 78',
            'is_active'   => true,
        ]);

        User::create([
            'name'        => 'Karim Tazi',
            'email'       => 'karim@pharmavisit.ma',
            'password'    => Hash::make('password'),
            'employee_id' => 'REP-002',
            'territory_id'=> $rabat->id,
            'phone'       => '+212 6 98 76 54 32',
            'is_active'   => true,
        ]);

        User::create([
            'name'        => 'Nadia El Fassi',
            'email'       => 'nadia@pharmavisit.ma',
            'password'    => Hash::make('password'),
            'employee_id' => 'REP-003',
            'territory_id'=> $casa->id,
            'phone'       => '+212 6 55 44 33 22',
            'is_active'   => true,
        ]);

        // ─── Doctors (Rabat territory - from Scraped CSV) ─────────────
        $csvPath = base_path('data-pipeline/output/raw_doctors.csv');
        if (file_exists($csvPath) && ($handle = fopen($csvPath, 'r')) !== false) {
            $header = fgetcsv($handle);
            while (($row = fgetcsv($handle)) !== false) {
                if (count($row) < 11) continue;

                // Remove Tifinagh (Shlha) and Arabic characters, plus extra spaces
                $row = array_map(function($val) {
                    $clean = preg_replace('/[\x{2D30}-\x{2D7F}\x{0600}-\x{06FF}]+/u', '', $val);
                    return trim(preg_replace('/\s+/', ' ', $clean));
                }, $row);
                
                Doctor::create([
                    'territory_id' => $rabat->id,
                    'first_name'   => $row[0] ?: 'Dr',
                    'last_name'    => $row[1] ?: 'Unknown',
                    'specialty'    => $row[2] ?: 'Médecine Générale',
                    'clinic_name'  => null,
                    'address'      => $row[3] ?: 'Rabat',
                    'city'         => $row[4] ?: 'Rabat',
                    'postal_code'  => $row[5] ?: '10000',
                    'region'       => $row[6] ?: 'Rabat-Salé-Kénitra',
                    'lat'          => is_numeric($row[9]) ? (float)$row[9] : null,
                    'lng'          => is_numeric($row[10]) ? (float)$row[10] : null,
                    'geocoded_at'  => now(),
                    'phone'        => $row[7] ?: ('+212 5 37 ' . rand(10, 99) . ' ' . rand(10, 99) . ' ' . rand(10, 99)),
                    'priority'     => ['high', 'medium', 'low'][array_rand(['high', 'medium', 'low'])],
                    'is_active'    => true,
                ]);
            }
            fclose($handle);
        }

        // ─── Doctors (Casablanca territory) ───────────────────────────
        $casaDoctors = [
            ['Houda',    'El Amrani',  'Cardiologie',       'Clinique du Parc',  '13 Rue du Parc',                'Casablanca', '20000', -7.6192, 33.5897, 'high'],
            ['Rachid',   'Sebti',      'Neurologie',        null,                '22 Boulevard Zerktouni',        'Casablanca', '20050', -7.6333, 33.5922, 'high'],
            ['Asmaa',    'El Kadiri',  'Gynécologie',       'Clinique Atlas',    '5 Rue Atlas',                   'Casablanca', '20000', -7.6200, 33.5880, 'medium'],
            ['Kamal',    'Benali',     'Pédiatrie',         null,                '17 Avenue Hassan II',           'Casablanca', '20000', -7.6178, 33.5908, 'medium'],
            ['Nour',     'Tahiri',     'Médecine Générale', 'Cabinet Tahiri',    '8 Rue Béni Mellal',             'Casablanca', '20100', -7.6154, 33.5832, 'low'],
            ['Anas',     'Mzabi',      'Dermatologie',      null,                '41 Boulevard d\'Anfa',          'Casablanca', '20000', -7.6389, 33.5956, 'medium'],
            ['Hind',     'Belkadi',    'Endocrinologie',    'Polyclinique CNSS', 'Avenue Hassan II',              'Casablanca', '20020', -7.6210, 33.5912, 'high'],
        ];

        foreach ($casaDoctors as [$fn, $ln, $spec, $clinic, $addr, $city, $zip, $lng, $lat, $prio]) {
            Doctor::create([
                'territory_id' => $casa->id,
                'first_name'   => $fn,
                'last_name'    => $ln,
                'specialty'    => $spec,
                'clinic_name'  => $clinic,
                'address'      => $addr,
                'city'         => $city,
                'postal_code'  => $zip,
                'region'       => 'Casablanca-Settat',
                'lat'          => $lat,
                'lng'          => $lng,
                'geocoded_at'  => now(),
                'phone'        => '+212 5 22 ' . rand(10, 99) . ' ' . rand(10, 99) . ' ' . rand(10, 99),
                'priority'     => $prio,
                'is_active'    => true,
            ]);
        }

        // ─── Pharmacies (Rabat territory) ─────────────────────────────
        $rabatPharmacies = [
            ['Pharmacie Al Farabi',     '14 Avenue Mohammed V',          'Rabat',   '10000', -6.8498, 33.9716, 'M. Khalid Fassi'],
            ['Pharmacie Agdal',         '7 Rue Oued Fès, Agdal',         'Rabat',   '10080', -6.8610, 33.9901, 'Mme. Nadia Sefrioui'],
            ['Pharmacie Hassan II',     '52 Boulevard Hassan II',        'Rabat',   '10020', -6.8530, 33.9820, 'M. Amine Tazi'],
            ['Pharmacie Hay Riad',      '98 Avenue Mehdi Ben Barka',     'Rabat',   '10100', -6.8710, 33.9590, 'Mme. Salma Alaoui'],
            ['Pharmacie Ibn Sina',      'Avenue Ibn Sina, Souissi',      'Rabat',   '10050', -6.8440, 33.9875, 'M. Omar Filali'],
            ['Pharmacie Salé Medina',   '15 Boulevard Bab Mrisa',        'Salé',    '11000', -6.8010, 34.0380, 'M. Youssef Bennis'],
            ['Pharmacie Témara Centre', '5 Avenue Mohammed VI',          'Témara',  '12000', -6.9110, 33.9230, 'Mme. Ilham Zidane'],
        ];

        foreach ($rabatPharmacies as [$name, $addr, $city, $zip, $lng, $lat, $mgr]) {
            Pharmacy::create([
                'territory_id' => $rabat->id,
                'name'         => $name,
                'address'      => $addr,
                'city'         => $city,
                'postal_code'  => $zip,
                'region'       => 'Rabat-Salé-Kénitra',
                'lat'          => $lat,
                'lng'          => $lng,
                'geocoded_at'  => now(),
                'phone'        => '+212 5 37 ' . rand(10, 99) . ' ' . rand(10, 99) . ' ' . rand(10, 99),
                'manager_name' => $mgr,
                'is_active'    => true,
            ]);
        }

        // ─── Pharmacies (Casablanca territory) ────────────────────────
        $casaPharmacies = [
            ['Pharmacie du Parc',    '13 Rue du Parc',           'Casablanca', '20000', -7.6192, 33.5897, 'M. Said Khaldi'],
            ['Pharmacie Zerktouni', '18 Bd Zerktouni',           'Casablanca', '20050', -7.6330, 33.5920, 'Mme. Fatna Berrada'],
            ['Pharmacie Anfa',      '33 Boulevard d\'Anfa',      'Casablanca', '20000', -7.6390, 33.5950, 'M. Badr El Kadi'],
            ['Pharmacie Maarif',    '9 Rue Abou Abdallah',       'Casablanca', '20100', -7.6350, 33.5880, 'Mme. Sanaa Guessous'],
        ];

        foreach ($casaPharmacies as [$name, $addr, $city, $zip, $lng, $lat, $mgr]) {
            Pharmacy::create([
                'territory_id' => $casa->id,
                'name'         => $name,
                'address'      => $addr,
                'city'         => $city,
                'postal_code'  => $zip,
                'region'       => 'Casablanca-Settat',
                'lat'          => $lat,
                'lng'          => $lng,
                'geocoded_at'  => now(),
                'phone'        => '+212 5 22 ' . rand(10, 99) . ' ' . rand(10, 99) . ' ' . rand(10, 99),
                'manager_name' => $mgr,
                'is_active'    => true,
            ]);
        }

        $this->command->info('✅ Seeded: 2 territories, 3 reps, Scraped doctors, 11 pharmacies');
        $this->command->info('   Login: sarah@pharmavisit.ma / password (Rabat territory)');
        $this->command->info('   Login: nadia@pharmavisit.ma / password (Casablanca territory)');
    }
}
