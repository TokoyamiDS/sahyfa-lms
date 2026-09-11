import assert from 'node:assert/strict'
import { describe, it } from 'bun:test'

const digits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']

function toPersianDigits(value) {
  return String(value).replace(/\d/g, digit => digits[Number(digit)])
}

describe('Jalali display conventions', () => {
  it('converts Latin digits to Persian digits without changing punctuation', () => {
    assert.equal(toPersianDigits('1403/01/02'), '۱۴۰۳/۰۱/۰۲')
    assert.equal(toPersianDigits('12.50'), '۱۲.۵۰')
  })
})
