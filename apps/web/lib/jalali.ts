import {
  format as formatJalali,
  formatDistanceToNow as formatJalaliDistanceToNow,
} from 'date-fns-jalali'

const PERSIAN_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']

export function toPersianDigits(value: string | number): string {
  return String(value).replace(/\d/g, digit => PERSIAN_DIGITS[Number(digit)])
}

export function formatJalaliDate(
  value: Date | number | string,
  pattern = 'yyyy/MM/dd',
  persianDigits = true,
): string {
  const formatted = formatJalali(new Date(value), pattern)
  return persianDigits ? toPersianDigits(formatted) : formatted
}

export function formatJalaliDistance(
  value: Date | number | string,
  options?: Parameters<typeof formatJalaliDistanceToNow>[1],
): string {
  return formatJalaliDistanceToNow(new Date(value), options)
}
