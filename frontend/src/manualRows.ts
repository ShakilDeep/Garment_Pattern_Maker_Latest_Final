import type {Measurement} from './types';
const required=['back_length_hps','front_length_hps','half_chest','half_waist','half_bottom_opening','yoke_depth_cb','shoulder_slope','shoulder_point_to_point','half_armhole_straight','half_bicep','sleeve_cap_height','sleeve_length','cuff_width','cuff_edge_to_edge','sleeve_placket_length','sleeve_placket_width','collar_width_cb','collar_band_width_cb','neck_width','front_neck_drop','front_placket_width'];
export function withManualRows(rows:Measurement[]):Measurement[]{
 const missing=required.filter(key=>!rows.some(r=>r.key===key));
 return [...rows,...missing.map(key=>({key,code:key,label:key.replaceAll('_',' '),unit:'cm',tolerance:null,source:'Manual entry',sheet:'',row:0,values:{}}))];
}
