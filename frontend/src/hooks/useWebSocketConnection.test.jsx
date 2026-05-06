import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useWebSocketConnection } from './useWebSocketConnection';

const mockGetValidAccessToken = vi.fn();
const sockets = [];

vi.mock('../utils/api', () => ({
  getValidAccessToken: (...args) => mockGetValidAccessToken(...args),
}));

class MockWebSocket {
  static OPEN = 1;

  constructor(url) {
    this.url = url;
    this.readyState = 0;
    this.close = vi.fn(() => {
      this.readyState = 3;
    });
    this.send = vi.fn();
    sockets.push(this);
  }
}

describe('useWebSocketConnection', () => {
  beforeEach(() => {
    sockets.length = 0;
    mockGetValidAccessToken.mockReset();
    vi.stubGlobal('WebSocket', MockWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('connects with a JWT query parameter instead of calling ws_auth', async () => {
    mockGetValidAccessToken.mockResolvedValue('test-access-token');

    const onMessage = vi.fn();
    const onError = vi.fn();
    const onClose = vi.fn();
    const onOpen = vi.fn();

    const { result } = renderHook(() =>
      useWebSocketConnection(42, onMessage, onError, onClose, onOpen)
    );

    await waitFor(() => {
      expect(mockGetValidAccessToken).toHaveBeenCalledTimes(1);
      expect(sockets).toHaveLength(1);
    });

    expect(sockets[0].url).toBe(
      'ws://localhost:8000/ws/profile_42/?token=test-access-token'
    );

    act(() => {
      sockets[0].readyState = MockWebSocket.OPEN;
      sockets[0].onopen();
    });

    expect(result.current.isConnected).toBe(true);
    expect(onOpen).toHaveBeenCalledTimes(1);
  });
});
