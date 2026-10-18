//! C-ABI surface for WebAssembly (no wasm-bindgen needed).
//! JS flow: ptr = pf_alloc(n); write request bytes; out = pf_call(ptr, n);
//! len = u32le at out; read len bytes at out+4; pf_free(out, len+4); pf_free(ptr, n).
use crate::api;

#[no_mangle]
pub extern "C" fn pf_alloc(len: usize) -> *mut u8 {
    let mut v: Vec<u8> = Vec::with_capacity(len.max(1));
    let p = v.as_mut_ptr();
    std::mem::forget(v);
    p
}

/// # Safety
/// `ptr` must come from `pf_alloc(cap)` / `pf_call` with the same capacity.
#[no_mangle]
pub unsafe extern "C" fn pf_free(ptr: *mut u8, cap: usize) {
    if !ptr.is_null() {
        drop(Vec::from_raw_parts(ptr, 0, cap.max(1)));
    }
}

/// # Safety
/// `ptr..ptr+len` must be readable memory.
#[no_mangle]
pub unsafe extern "C" fn pf_call(ptr: *const u8, len: usize) -> *mut u8 {
    let bytes = std::slice::from_raw_parts(ptr, len);
    let req = std::str::from_utf8(bytes).unwrap_or("");
    let out = api::call(req).into_bytes();
    let mut buf: Vec<u8> = Vec::with_capacity(out.len() + 4);
    buf.extend_from_slice(&(out.len() as u32).to_le_bytes());
    buf.extend_from_slice(&out);
    let boxed = buf.into_boxed_slice();
    Box::into_raw(boxed) as *mut u8
}
