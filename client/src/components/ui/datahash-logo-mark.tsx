import { cn } from "@/lib/utils";

const SIZE_CLASSES = {
  sm: {
    box: "h-7 w-7",
    image: "h-4 w-4",
  },
  md: {
    box: "h-9 w-9",
    image: "h-5 w-5",
  },
} as const;

export function DatahashLogoMark({
  size = "md",
  className,
}: {
  size?: keyof typeof SIZE_CLASSES;
  className?: string;
}) {
  const { box, image } = SIZE_CLASSES[size];

  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--card)] p-1.5",
        box,
        className,
      )}
    >
      <img
        src="/datahash-logo.svg"
        alt="Datahash"
        className={cn("object-contain", image)}
      />
    </div>
  );
}
