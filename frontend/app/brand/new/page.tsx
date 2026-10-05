'use client';

/** Brand · List a product. A live image preview on the right; on submit the
 *  product is scored against every creator straight away. */
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useBrands } from '@/components/BrandContext';
import { Chip, ProductImage } from '@/components/ui';
import { api, BASE, imgSrc } from '@/lib/api';
import { PACKS, type Niche } from '@/lib/types';

const CATEGORIES: Niche[] = ['Skincare', 'Makeup', 'Haircare', 'Personal Care'];
const MAX_IMAGE_BYTES = 350_000;

export default function NewProductPage() {
  const { current, loading, invalidate, refresh } = useBrands();
  const router = useRouter();
  const [f, setF] = useState({
    title: '',
    category: 'Skincare' as Niche,
    sub_category: '',
    price: 399,
    description: '',
    tags: '',
    pack: '',
    age_min: 18,
    age_max: 30,
    tiers: ['T1', 'T2', 'T3'] as string[],
  });
  const [photo, setPhoto] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (loading || !current) return <Loading label="Loading brands" />;

  const previewUrl = photo
    ? photo
    : `${BASE}/imagery/preview.svg?${new URLSearchParams({
        title: f.title || 'Product',
        category: f.category,
        pack: f.pack,
        seed: f.title || 'new',
      })}`;

  function onFile(file: File | undefined) {
    if (!file) return;
    if (file.size > MAX_IMAGE_BYTES) {
      setError('That photo is over 350 KB. Resize it, or leave it out and use the drawn image.');
      return;
    }
    setError(null);
    const reader = new FileReader();
    reader.onload = () => setPhoto(String(reader.result));
    reader.readAsDataURL(file);
  }

  async function submit() {
    if (!current) return;
    setBusy(true);
    setError(null);
    try {
      const p = await api.createProduct({
        title: f.title,
        brand: current.brand,
        category: f.category,
        sub_category: f.sub_category,
        price: f.price,
        description: f.description,
        tags: f.tags.split(',').map((t) => t.trim()).filter(Boolean),
        pack: f.pack,
        target_age_min: f.age_min,
        target_age_max: f.age_max,
        target_tiers: f.tiers,
        image_url: photo,
      });
      await refresh();
      invalidate();
      router.push(`/brand/product/${p.product_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not list the product.');
      setBusy(false);
    }
  }

  const valid = f.title.trim().length >= 2 && f.price >= 10 && f.age_min <= f.age_max && f.tiers.length > 0;

  return (
    <>
      <PageHeader
        title="List a product"
        description={`Added under ${current.brand}. As soon as it is listed you will see which creators it fits.`}
      />
      {error && <ErrorState message={error} />}

      <div className="grid gap-6 px-6 pb-16 pt-5 lg:grid-cols-[1fr_360px]">
        <section className="panel p-6">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="md:col-span-2">
              <span className="field-label">Product name</span>
              <input className="field" value={f.title} placeholder="e.g. Aloe Hydra Gel" onChange={(e) => setF({ ...f, title: e.target.value })} />
            </label>
            <label>
              <span className="field-label">Category</span>
              <select className="field" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value as Niche })}>
                {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
            <label>
              <span className="field-label">Price (₹)</span>
              <input type="number" className="field" value={f.price} min={10} onChange={(e) => setF({ ...f, price: +e.target.value })} />
            </label>
            <label>
              <span className="field-label">Sub-category</span>
              <input className="field" value={f.sub_category} placeholder="serum, lips, shampoo…" onChange={(e) => setF({ ...f, sub_category: e.target.value })} />
            </label>
            <label>
              <span className="field-label">Tags (comma separated)</span>
              <input className="field" value={f.tags} placeholder="hydrating, daily-use, affordable" onChange={(e) => setF({ ...f, tags: e.target.value })} />
            </label>
            <label className="md:col-span-2">
              <span className="field-label">Description</span>
              <textarea rows={2} className="field" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label>
                <span className="field-label">Made for ages</span>
                <input type="number" className="field" value={f.age_min} onChange={(e) => setF({ ...f, age_min: +e.target.value })} />
              </label>
              <label>
                <span className="field-label">to</span>
                <input type="number" className="field" value={f.age_max} onChange={(e) => setF({ ...f, age_max: +e.target.value })} />
              </label>
            </div>
            <div>
              <span className="field-label">Audience tiers</span>
              <div className="flex gap-1.5">
                {['T1', 'T2', 'T3'].map((t) => (
                  <Chip
                    key={t}
                    active={f.tiers.includes(t)}
                    onClick={() => setF({ ...f, tiers: f.tiers.includes(t) ? f.tiers.filter((x) => x !== t) : [...f.tiers, t] })}
                  >
                    Tier {t.slice(1)}
                  </Chip>
                ))}
              </div>
            </div>
            <div className="md:col-span-2">
              <span className="field-label">Pack style (for the drawn image)</span>
              <div className="flex flex-wrap gap-1.5">
                <Chip active={f.pack === ''} onClick={() => setF({ ...f, pack: '' })}>Auto</Chip>
                {PACKS.map((p) => (
                  <Chip key={p.value} active={f.pack === p.value} onClick={() => setF({ ...f, pack: p.value })}>
                    {p.label}
                  </Chip>
                ))}
              </div>
            </div>
            <div className="md:col-span-2">
              <span className="field-label">Or use your own photo</span>
              <input type="file" accept="image/*" onChange={(e) => onFile(e.target.files?.[0])} className="text-[12.5px]" />
              {photo && (
                <button className="ml-3 text-[12px] text-[var(--signal)]" onClick={() => setPhoto(null)}>
                  remove photo
                </button>
              )}
            </div>
          </div>
          <button className="btn mt-6" disabled={!valid || busy} onClick={() => void submit()}>
            {busy ? 'Listing…' : 'List product and find creators'}
          </button>
        </section>

        <aside className="self-start">
          <p className="mb-2 text-[12px] font-medium text-[var(--ink-3)]">Preview</p>
          <div className="card">
            <ProductImage src={previewUrl} alt="Product preview" className="aspect-square w-full" />
            <div className="p-4">
              <p className="text-[11.5px] text-[var(--ink-3)]">{current.brand}</p>
              <p className="text-[15px] font-semibold">{f.title || 'Product name'}</p>
              <p className="mt-1 text-[13px] font-semibold">₹{f.price}</p>
              <span className="mt-2 inline-block rounded-full border border-[var(--signal)] px-2.5 py-0.5 text-[11px] font-semibold text-[var(--signal)]">
                New listing
              </span>
            </div>
          </div>
          <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--ink-3)]">
            Without a photo the image is drawn from the name and pack style. New listings start with no
            reviews, so early offers matter most.
          </p>
        </aside>
      </div>
    </>
  );
}
