/**
 * Unit tests — src/context/ToastContext.jsx
 *
 * Covers: toast appears on addToast, success/error types, auto-dismiss,
 * multiple toasts stacked independently.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, act, screen } from '@testing-library/react'
import { ToastProvider, useToast } from '../context/ToastContext'

vi.useFakeTimers()

function ToastTrigger({ message, type }) {
  const addToast = useToast()
  return (
    <button onClick={() => addToast(message, type)}>
      Show Toast
    </button>
  )
}

function Wrapped({ message = 'Test message', type = 'error' }) {
  return (
    <ToastProvider>
      <ToastTrigger message={message} type={type} />
    </ToastProvider>
  )
}

afterEach(() => {
  vi.clearAllTimers()
})

describe('ToastContext', () => {
  it('toast appears after addToast is called', async () => {
    render(<Wrapped message="Something went wrong" />)
    await act(async () => { screen.getByText('Show Toast').click() })
    expect(screen.getByText('Something went wrong')).toBeTruthy()
  })

  it('toast auto-dismisses after 4 seconds', async () => {
    render(<Wrapped message="Auto dismiss me" />)
    await act(async () => { screen.getByText('Show Toast').click() })
    expect(screen.getByText('Auto dismiss me')).toBeTruthy()

    await act(async () => { vi.advanceTimersByTime(4100) })
    expect(screen.queryByText('Auto dismiss me')).toBeNull()
  })

  it('toast still present before 4 seconds', async () => {
    render(<Wrapped message="Still here" />)
    await act(async () => { screen.getByText('Show Toast').click() })
    await act(async () => { vi.advanceTimersByTime(3000) })
    expect(screen.getByText('Still here')).toBeTruthy()
  })

  it('success type toast renders', async () => {
    render(<Wrapped message="Saved!" type="success" />)
    await act(async () => { screen.getByText('Show Toast').click() })
    expect(screen.getByText('Saved!')).toBeTruthy()
  })

  it('multiple toasts can exist simultaneously', async () => {
    function MultiTrigger() {
      const addToast = useToast()
      return (
        <>
          <button data-testid="btn-first" onClick={() => addToast('First toast')}>TriggerFirst</button>
          <button data-testid="btn-second" onClick={() => addToast('Second toast')}>TriggerSecond</button>
        </>
      )
    }
    render(<ToastProvider><MultiTrigger /></ToastProvider>)

    await act(async () => { screen.getByTestId('btn-first').click() })
    await act(async () => { screen.getByTestId('btn-second').click() })

    expect(screen.getByText('First toast')).toBeTruthy()
    expect(screen.getByText('Second toast')).toBeTruthy()
  })

  it('each toast dismisses independently', async () => {
    function MultiTrigger() {
      const addToast = useToast()
      return (
        <>
          <button data-testid="btn-alpha" onClick={() => addToast('Alpha toast')}>TriggerAlpha</button>
          <button data-testid="btn-beta" onClick={() => addToast('Beta toast')}>TriggerBeta</button>
        </>
      )
    }
    render(<ToastProvider><MultiTrigger /></ToastProvider>)

    await act(async () => { screen.getByTestId('btn-alpha').click() })
    await act(async () => { vi.advanceTimersByTime(1000) })
    await act(async () => { screen.getByTestId('btn-beta').click() })
    await act(async () => { vi.advanceTimersByTime(3100) })

    // Alpha (4s total elapsed since click) should be dismissed
    expect(screen.queryByText('Alpha toast')).toBeNull()
    // Beta (only 3.1s since its click) should still be visible
    expect(screen.getByText('Beta toast')).toBeTruthy()
  })
})
