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

        // ─── Doctors (Rabat territory) ────────────────────────────────
        $rabatDoctors = [
            ['Amina',    'Chraibi',   'Cardiologie',        'Clinique Al Farabi',   '14 Avenue Mohammed V',             'Rabat',    '10000', -6.8498, 33.9716, 'high'],
            ['Hassan',   'Ouazzani',  'Pédiatrie',          'Cabinet Ouazzani',     '7 Rue Patrice Lumumba',            'Rabat',    '10000', -6.8412, 33.9768, 'high'],
            ['Fatima',   'El Idrissi','Médecine Générale',  null,                   '23 Avenue Al Amir Fal Ould Omer',  'Salé',     '11000', -6.7985, 34.0311, 'medium'],
            ['Youssef',  'Berrada',   'Neurologie',         'Centre Neurologique',  '45 Boulevard Hassan II',           'Rabat',    '10020', -6.8527, 33.9824, 'high'],
            ['Khadija',  'Mansouri',  'Gynécologie',        'Polyclinique Agdal',   '3 Rue Oued Fès, Agdal',            'Rabat',    '10080', -6.8605, 33.9904, 'medium'],
            ['Mohamed',  'Lahlou',    'Ophtalmologie',      'Cabinet Lahlou',       '18 Avenue Fal Ould Omer',          'Rabat',    '10000', -6.8490, 33.9800, 'medium'],
            ['Samir',    'Bennani',   'Dermatologie',       null,                   '9 Rue Soussa',                     'Salé',     '11000', -6.8005, 34.0378, 'low'],
            ['Rim',      'Tazi',      'Endocrinologie',     'Clinique Al Amal',     '67 Avenue Hassan II',              'Rabat',    '10020', -6.8533, 33.9831, 'high'],
            ['Omar',     'Filali',    'Pneumologie',        null,                   '5 Rue Doukala',                    'Rabat',    '10000', -6.8467, 33.9743, 'medium'],
            ['Zineb',    'Alaoui',    'Rhumatologie',       'Centre Méd. Hay Riad', '120 Avenue Mehdi Ben Barka',       'Rabat',    '10100', -6.8714, 33.9597, 'medium'],
            ['Abdelkrim','Hakimi',    'Chirurgie Générale', 'Clinique Cheikh Zaïd', 'Hay Riad',                         'Rabat',    '10100', -6.8700, 33.9600, 'high'],
            ['Souad',    'Marzouki',  'Cardiologie',        null,                   '2 Avenue Ibn Sina',                'Rabat',    '10050', -6.8445, 33.9873, 'high'],
            ['Mehdi',    'Boussaid',  'Médecine Interne',   'Hôpital Ibn Sina',     'Avenue Ibn Sina',                  'Rabat',    '10050', -6.8444, 33.9878, 'medium'],
            ['Leila',    'Cherkaoui', 'Pédiatrie',          null,                   '34 Rue Moulay Rachid, Témara',     'Témara',   '12000', -6.9108, 33.9226, 'low'],
            ['Aziz',     'Zniber',    'Médecine Générale',  'Cabinet Médical',      '11 Boulevard Al Massira',          'Salé',     '11000', -6.7978, 34.0378, 'medium'],
        ];

        foreach ($rabatDoctors as [$fn, $ln, $spec, $clinic, $addr, $city, $zip, $lng, $lat, $prio]) {
            Doctor::create([
                'territory_id' => $rabat->id,
                'first_name'   => $fn,
                'last_name'    => $ln,
                'specialty'    => $spec,
                'clinic_name'  => $clinic,
                'address'      => $addr,
                'city'         => $city,
                'postal_code'  => $zip,
                'region'       => 'Rabat-Salé-Kénitra',
                'lat'          => $lat,
                'lng'          => $lng,
                'geocoded_at'  => now(),
                'phone'        => '+212 5 37 ' . rand(10, 99) . ' ' . rand(10, 99) . ' ' . rand(10, 99),
                'priority'     => $prio,
                'is_active'    => true,
            ]);
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

        $this->command->info('✅ Seeded: 2 territories, 3 reps, 22 doctors, 11 pharmacies');
        $this->command->info('   Login: sarah@pharmavisit.ma / password (Rabat territory)');
        $this->command->info('   Login: nadia@pharmavisit.ma / password (Casablanca territory)');
    }
}
