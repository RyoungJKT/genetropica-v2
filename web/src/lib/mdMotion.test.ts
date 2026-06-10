import { readFileSync } from 'node:fs'
import { describe, it, expect } from 'vitest'
import type { Md } from '../data/types'
import { distanceAt, ligandRmsdAt, proteinRmsdAt, hbondsAt, ncontactsAt, rmsfFor, residueCount, frameReadout, DURATION_NS } from './mdMotion'

const md: Md = JSON.parse(readFileSync(new URL('../../public/data/md.json', import.meta.url), 'utf8'))
const cele = md.series.celecoxib
const metho = md.series.methotrexate
const dasa = md.series.dasabuvir

describe('distanceAt (real trajectory)', () => {
  it('celecoxib starts far and associates fast', () => {
    expect(distanceAt(cele, 0)).toBeGreaterThan(18)
    expect(distanceAt(cele, 5)).toBeLessThan(3)
    expect(distanceAt(cele, 50)).toBeLessThan(5)
  })
  it('methotrexate is still far at 5 ns and associated by 25 ns', () => {
    expect(distanceAt(metho, 5)).toBeGreaterThan(10)
    expect(distanceAt(metho, 25)).toBeLessThan(3)
  })
  it('dasabuvir never settles', () => {
    expect(distanceAt(dasa, 25)).toBeGreaterThan(10)
    expect(distanceAt(dasa, 50)).toBeGreaterThan(5)
  })
})

describe('ligandRmsdAt', () => {
  it('is null for dasabuvir (no stable pose, zero ligand-RMSD points)', () => {
    expect(ligandRmsdAt(dasa, 25)).toBeNull()
  })
  it('is a number for celecoxib once associated', () => {
    expect(typeof ligandRmsdAt(cele, 25)).toBe('number')
  })
})

describe('counts and per-residue', () => {
  it('hbonds and ncontacts are non-negative integers in range', () => {
    expect(Number.isInteger(hbondsAt(cele, 25))).toBe(true)
    expect(hbondsAt(cele, 25)).toBeGreaterThanOrEqual(0)
    expect(ncontactsAt(cele, 25)).toBeGreaterThanOrEqual(0)
  })
  it('proteinRmsdAt is a finite positive number', () => {
    expect(proteinRmsdAt(cele, 25)).toBeGreaterThan(0)
  })
  it('residueCount is 849 and rmsfFor returns a positive value', () => {
    expect(residueCount(cele)).toBe(849)
    expect(rmsfFor(cele, 0)).toBeGreaterThan(0)
    expect(rmsfFor(cele, 10_000)).toBeGreaterThan(0) // clamps out-of-range index
  })
})

describe('frameReadout and constants', () => {
  it('returns the live readout fields and DURATION_NS is 50', () => {
    const r = frameReadout(cele, 12.5)
    expect(r.tNs).toBe(12.5)
    expect(r.distance).toBeGreaterThan(0)
    expect(DURATION_NS).toBe(50)
  })
})
