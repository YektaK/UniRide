# Menu-infeasible wording: proposed sentence changes for DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md

Kapsam: yalnızca gün düzeyi uygunsuzluk ifadeleri. Sayılar, etiket adları ve diğer cümleler aynen kalır. Yöntem belgesi düzenlenmedi; şef aşağıdaki YENİ cümleleri uygular.

## Değişiklikler

### 1. §6 Heterogeneous fleet scenarios, tablo notu (satır ~173)

ESKİ:
> An x denotes a menu-infeasible weekday; a dash denotes an unavailable weekly count because at least one weekday is infeasible.

YENİ:
> An x denotes a menu-infeasible weekday; a dash denotes an unavailable weekly count because at least one weekday is menu-infeasible.

### 2. §6, L2 maddesi (satır ~180)

ESKİ:
> Of its 9 infeasible cells, 2 are labelled `SW_DEMAND_EXCEEDS_LARGE_CAPACITY` (Monday at R = 50 and 60) and 7 `CROSS_WAVE_CONFLICT`.

YENİ:
> Of its 9 menu-infeasible cells, 2 are labelled `SW_DEMAND_EXCEEDS_LARGE_CAPACITY` (Monday at R = 50 and 60) and 7 `CROSS_WAVE_CONFLICT`.

### 3. §6, kanıt etiketleri paragrafı (satır ~185)

ESKİ:
> The proof label `proven_over_menu` applies to borrowed-vehicle count over the generated menus; a different routing could change the count, and `infeasible_for_L` means no feasible selection within those menus.

YENİ:
> The proof label `proven_over_menu` applies to borrowed-vehicle count over the generated menus; a different routing could change the count, and `infeasible_for_L` means infeasible over the generated menus (menu-infeasible), not that no feasible day plan exists.

### 4. §6 Multi-objective trade-off, ε-constraint paragrafı (satır ~191)

ESKİ:
> The recorded route/CSV checks cover 131 feasible-day runs with zero violations and 29 infeasible-day runs with no routes.

YENİ:
> The recorded route/CSV checks cover 131 feasible-day runs with zero violations and 29 menu-infeasible day runs with no routes.

Not: aynı belge satır ~150'de bu satırlar için zaten "menu-infeasible rows" diyor; değişiklik ifadeyi onunla aynı yapar.

### 5. §7 Method, "Day level" paragrafı (satır ~234)

ESKİ:
> The union-menu result is the minimum car count over that union menu, not a global day optimum, because no day-level exact model was solved (out of scope).

YENİ:
> The union-menu result is the minimum car count over that union menu, not a global day optimum, because no day-level exact model was solved (out of scope); for the same reason, a run labelled `infeasible_for_L` is infeasible over its menu, not proven infeasible for the day.

## Değiştirilmeyen cümleler

- Satır ~173, ilk yarı ("An x denotes a menu-infeasible weekday"): zaten "menu-infeasible" diyor.
- Satır ~179, "**L1 has no feasible menu selection.** All 20 cells are `infeasible_for_L`: ...": başlık cümlesi uygunsuzluğu menüye bağlıyor, etiket de 3. değişiklikteki tanıma bağlanıyor.
- Satır ~180, "It is feasible on 2 of 5 days ... so none of these generated-menu scenarios provides a complete week with two minibuses": cümle zaten "generated-menu" diyor.
- Satır ~150, "29 menu-infeasible rows with no routes": zaten açık.
- Satır ~152 ve ~210 ("proven over menus", "Borrowed count is proven only over those menus"): uygunluk ve sayı iddiası, menüye bağlı.
- Satır ~191, "of which 28 are feasible" ve "a weekly option requires a feasible selection on all five weekdays": uygunluk iddiası; paragrafın ilk cümlesi seçimi "over its generated route menus" diye sınırlıyor.
- Tablo 7.2 sütun başlıkları "Both menus infeasible" ve "GA-menu run proven infeasible, union run optimal and confirmed": ikisi de uygunsuzluğu menüye bağlıyor; 5. değişiklik bu sütunların okunuşunu yöntem paragrafında sabitliyor.
- Satır ~253, "167 were proven infeasible" ve "In 2 options the GA found no solution": dalga düzeyindeki seçenekler; gün düzeyi değil, bu işin kapsamı dışında.

## Değişiklik gerekip kapsam dışında kalan yerler

- Satır ~234, "(out of scope)": E13, E01'deki EQ3 kısmının ("a global day model is out of scope") yerini aldı; global gün modeli artık WP-E11 olarak planlı. 5. değişiklik bu parantezi aynen korur. Parantezin yeniden yazılması karar gerektirir: [EKSİK: E13 sonrası "(out of scope)" yerine ne yazılacağı, ör. "not part of this study", şef/sahip kararı].
- Satır ~276 (§8), "a joint optimum over all route sets and vehicle types remains outside their evidence": uygunsuzluk ifadesi değil; E13 sonrası §8'e WP-E11'in eklenip eklenmeyeceği ayrı bir karar.
- Yan gözlem, bu işle ilgisiz: satır ~278 GOAL 2 için "planned but not started; they wait for an owner decision" diyor; karar dosyası E09 ve E10 bu kararın alındığını ve WP-E7'nin yapıldığını kaydediyor. [EKSİK: bu satır için ayrı brif; bulgu listesinde yok]
