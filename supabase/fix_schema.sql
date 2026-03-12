-- UniRide Veritabanı Onarım Scripti
-- Supabase SQL Editor'da çalıştırın.

-- 1. accessibility_needs sütunu kontrolü ve eklenmesi
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='accessibility_needs') THEN
        ALTER TABLE users ADD COLUMN accessibility_needs TEXT[] DEFAULT '{}';
    END IF;
END $$;

-- 2. disability_type kısıtlamasının güncellenmesi (NULL değerlerine izin verir)
-- Önce eski kısıtlamayı kaldırıyoruz
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_disability_type_check;

-- Yeni kısıtlamayı ekliyoruz (Sw, So veya NULL)
ALTER TABLE users ADD CONSTRAINT users_disability_type_check 
    CHECK (disability_type IN ('Sw', 'So') OR disability_type IS NULL);

-- 3. Mevcut Admin ve Şoförlerin disability_type değerlerini null yapalım (temizlik)
UPDATE users SET disability_type = NULL WHERE role IN ('admin', 'driver');
UPDATE users SET accessibility_needs = '{}' WHERE role IN ('admin', 'driver');

-- 5. weekly_schedules tablosuna UNIQUE(user_id) kısıtlaması ekleme
-- Bu sayede her kullanıcının sadece bir programı olabilir ve upsert düzgün çalışır.
ALTER TABLE weekly_schedules DROP CONSTRAINT IF EXISTS weekly_schedules_user_id_key;
ALTER TABLE weekly_schedules ADD CONSTRAINT weekly_schedules_user_id_key UNIQUE (user_id);
