// Small date helpers for the gameweek calendar. All inputs are ISO strings.

export function fmtDay(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export function fmtTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtRange(startIso, endIso) {
  if (!startIso) return "Dates TBC";
  const start = fmtDay(startIso);
  const end = endIso ? fmtDay(endIso) : null;
  return end && end !== start ? `${start} – ${end}` : start;
}

export function monthLabel(iso) {
  if (!iso) return "Upcoming";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });
}
