'use client';

/**
 * InvoicePreviewModal — shows a PDF invoice in an iframe before (or instead of)
 * downloading it. Fetches the PDF as a blob URL to avoid CORS issues.
 *
 * Usage:
 *   <InvoicePreviewModal billId={id} onClose={close} />
 *
 * The modal handles its own loading / error state so callers don't need to.
 */

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { downloadInvoicePdf, getInvoicePreviewUrl } from '@/hooks/use-sales';

interface InvoicePreviewModalProps {
  billId: string;
  invoiceNumber: string;
  onClose: () => void;
}

export function InvoicePreviewModal({
  billId,
  invoiceNumber,
  onClose,
}: InvoicePreviewModalProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;

    async function load() {
      setLoading(true);
      setError(false);
      objectUrl = await getInvoicePreviewUrl(billId);
      if (objectUrl) {
        setPreviewUrl(objectUrl);
      } else {
        setError(true);
      }
      setLoading(false);
    }

    load();

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [billId]);

  const handleDownload = async () => {
    setDownloading(true);
    const ok = await downloadInvoicePdf(billId);
    setDownloading(false);
    if (!ok) toast.error('Failed to download PDF. Please try again.');
  };

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="flex flex-col bg-white rounded-xl shadow-2xl w-full max-w-3xl h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-stone-200 shrink-0">
          <div>
            <h2 className="text-sm font-semibold text-slate-700">Invoice Preview</h2>
            <p className="text-xs text-stone-400 font-mono">{invoiceNumber}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              disabled={downloading || loading}
              className="text-xs"
            >
              {downloading ? 'Downloading…' : '⬇ Download PDF'}
            </Button>
            <button
              onClick={onClose}
              className="text-stone-400 hover:text-stone-600 text-xl leading-none font-light px-1"
              aria-label="Close preview"
            >
              ×
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 min-h-0 p-2">
          {loading ? (
            <div className="h-full flex items-center justify-center">
              <div className="space-y-3 w-3/4">
                <Skeleton className="h-6 w-full" />
                <Skeleton className="h-4 w-5/6" />
                <Skeleton className="h-4 w-4/6" />
                <Skeleton className="h-32 w-full mt-4" />
              </div>
            </div>
          ) : error ? (
            <div className="h-full flex items-center justify-center text-center">
              <div className="space-y-3">
                <p className="text-stone-500">Could not load PDF preview.</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownload}
                  className="text-xs"
                >
                  Download directly instead
                </Button>
              </div>
            </div>
          ) : (
            <iframe
              src={previewUrl!}
              className="w-full h-full rounded border border-stone-200"
              title={`Invoice ${invoiceNumber}`}
            />
          )}
        </div>
      </div>
    </div>
  );
}
