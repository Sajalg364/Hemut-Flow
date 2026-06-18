/**
 * Raw XMLHttpRequest utility wrapper.
 * 
 * Uses XMLHttpRequest (NOT fetch/axios) to handle HTTP request lifecycle,
 * including async, progress, abort, timeout, and error events directly.
 */

/**
 * Make an XHR request.
 * @param {Object} options
 * @param {string} options.method - HTTP method
 * @param {string} options.url - Request URL
 * @param {Object} [options.data] - Request body (will be JSON stringified)
 * @param {Object} [options.headers] - Additional headers
 * @param {number} [options.timeout] - Timeout in ms (default 15000)
 * @param {Function} [options.onProgress] - Upload progress callback
 * @param {Function} [options.onDownloadProgress] - Download progress callback
 * @returns {Promise<{data: any, status: number, xhr: XMLHttpRequest}>}
 */
export function xhrRequest({
  method,
  url,
  data = null,
  headers = {},
  timeout = 15000,
  onProgress = null,
  onDownloadProgress = null,
}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url, true);

    // Set default headers
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('Accept', 'application/json');

    // Set custom headers
    Object.entries(headers).forEach(([key, value]) => {
      xhr.setRequestHeader(key, value);
    });

    // Set timeout
    xhr.timeout = timeout;

    // Handle successful response
    xhr.onload = function () {
      let responseData;
      try {
        responseData = JSON.parse(xhr.responseText);
      } catch {
        responseData = xhr.responseText;
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve({
          data: responseData,
          status: xhr.status,
          xhr: xhr,
        });
      } else {
        reject({
          data: responseData,
          status: xhr.status,
          message: responseData?.detail || `Request failed with status ${xhr.status}`,
          xhr: xhr,
        });
      }
    };

    // Handle network errors
    xhr.onerror = function () {
      reject({
        data: null,
        status: 0,
        message: 'Network error - please check your connection',
        xhr: xhr,
      });
    };

    // Handle timeout
    xhr.ontimeout = function () {
      reject({
        data: null,
        status: 0,
        message: 'Request timed out - please try again',
        xhr: xhr,
      });
    };

    // Handle abort
    xhr.onabort = function () {
      reject({
        data: null,
        status: 0,
        message: 'Request was aborted',
        xhr: xhr,
      });
    };

    // Upload progress tracking
    if (onProgress && xhr.upload) {
      xhr.upload.onprogress = function (event) {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent, event);
        }
      };
    }

    // Download progress tracking
    if (onDownloadProgress) {
      xhr.onprogress = function (event) {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onDownloadProgress(percent, event);
        }
      };
    }

    // Send request
    if (data) {
      xhr.send(JSON.stringify(data));
    } else {
      xhr.send();
    }
  });
}

/**
 * Convenience method for GET requests
 */
export function xhrGet(url, headers = {}) {
  return xhrRequest({ method: 'GET', url, headers });
}

/**
 * Convenience method for POST requests
 */
export function xhrPost(url, data, headers = {}) {
  return xhrRequest({ method: 'POST', url, data, headers });
}

export function xhrPut(url, data, headers = {}) {
  return xhrRequest({ method: 'PUT', url, data, headers });
}

export function xhrDelete(url, headers = {}) {
  return xhrRequest({ method: 'DELETE', url, headers });
}

/**
 * Create an XHR request that can be aborted
 * Returns { promise, abort }
 */
export function xhrAbortable({ method, url, data = null, headers = {}, timeout = 15000 }) {
  const xhr = new XMLHttpRequest();
  
  const promise = new Promise((resolve, reject) => {
    xhr.open(method, url, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('Accept', 'application/json');
    
    Object.entries(headers).forEach(([key, value]) => {
      xhr.setRequestHeader(key, value);
    });

    xhr.timeout = timeout;

    xhr.onload = function () {
      let responseData;
      try {
        responseData = JSON.parse(xhr.responseText);
      } catch {
        responseData = xhr.responseText;
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve({ data: responseData, status: xhr.status });
      } else {
        reject({ data: responseData, status: xhr.status, message: responseData?.detail || `Request failed` });
      }
    };

    xhr.onerror = () => reject({ status: 0, message: 'Network error' });
    xhr.ontimeout = () => reject({ status: 0, message: 'Request timed out' });
    xhr.onabort = () => reject({ status: 0, message: 'Request aborted' });

    if (data) {
      xhr.send(JSON.stringify(data));
    } else {
      xhr.send();
    }
  });

  return { promise, abort: () => xhr.abort() };
}
