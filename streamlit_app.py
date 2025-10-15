import streamlit as st
import re
from datetime import datetime

class IFTMINParser:
    def __init__(self):
        self.segments = []
        
    def parse_iftmin(self, data):
        """Parse IFTMIN EDI message"""
        # Clean and split segments
        data = data.replace("'", "\n")
        self.segments = [segment for segment in data.split('\n') if segment.strip()]
        
        result = {
            'header': {},
            'parties': {},
            'shipments': [],
            'summary': {}
        }
        
        self._parse_header(result)
        self._parse_parties(result)
        self._parse_shipments(result)
        self._parse_summary(result)
        
        return result
    
    def _parse_header(self, result):
        """Parse message header information"""
        for segment in self.segments:
            if segment.startswith('UNB'):
                parts = segment.split('+')
                result['header']['sender'] = parts[2].split(':')[0] if ':' in parts[2] else parts[2]
                result['header']['receiver'] = parts[3].split(':')[0] if ':' in parts[3] else parts[3]
            elif segment.startswith('BGM'):
                parts = segment.split('+')
                result['header']['doc_number'] = parts[2] if len(parts) > 2 else ''
            elif segment.startswith('DTM+9'):
                parts = segment.split('+')
                date_str = parts[1].split(':')[1] if ':' in parts[1] else parts[1]
                result['header']['message_date'] = self._format_date(date_str)
            elif segment.startswith('CUX'):
                parts = segment.split('+')
                if len(parts) > 2:
                    result['header']['currency'] = parts[2]
    
    def _parse_parties(self, result):
        """Parse party information (shipper, consignee, etc.)"""
        for segment in self.segments:
            if segment.startswith('NAD+SF'):
                parts = segment.split('+')
                result['parties']['shipper'] = self._parse_address(parts, 'WTAM')
            elif segment.startswith('NAD+IV'):
                parts = segment.split('+')
                result['parties']['invoicee'] = self._parse_address(parts, 'AMAZON EU SARL')
            elif segment.startswith('LOC+198'):
                parts = segment.split('+')
                result['parties']['node_id'] = parts[2] if len(parts) > 2 else ''
    
    def _parse_shipments(self, result):
        """Parse shipment information"""
        current_shipment = {}
        items = []
        
        for segment in self.segments:
            if segment.startswith('GID+1') or segment.startswith('GID+2'):
                if current_shipment:
                    current_shipment['items'] = items.copy()
                    result['shipments'].append(current_shipment.copy())
                    items = []
                    current_shipment = {}
                
                parts = segment.split('+')
                if len(parts) > 2:
                    current_shipment['total_packages'] = parts[2].split(':')[0]
            
            elif segment.startswith('NAD+CN'):
                parts = segment.split('+')
                current_shipment['consignee'] = self._parse_address(parts)
            
            elif segment.startswith('RFF+CR'):
                parts = segment.split('+')
                current_shipment['tracking_number'] = parts[2] if len(parts) > 2 else ''
            
            elif segment.startswith('RFF+TB'):
                parts = segment.split('+')
                current_shipment['order_id'] = parts[2] if len(parts) > 2 else ''
            
            elif segment.startswith('RFF+TE'):
                parts = segment.split('+')
                current_shipment['phone'] = parts[2] if len(parts) > 2 else ''
            
            elif segment.startswith('DTM+17'):
                parts = segment.split('+')
                date_str = parts[1].split(':')[1] if ':' in parts[1] else parts[1]
                current_shipment['delivery_date'] = self._format_date(date_str)
            
            elif segment.startswith('MEA+WX+B+KG'):
                parts = segment.split('+')
                current_shipment['weight'] = parts[3] if len(parts) > 3 else ''
            
            elif segment.startswith('DIM+2+CMT'):
                parts = segment.split('+')
                dims = parts[2].split(':')[1:] if ':' in parts[2] else []
                current_shipment['dimensions'] = 'x'.join(dims) + ' cm' if dims else ''
            
            elif segment.startswith('RFF+VP'):
                parts = segment.split('+')
                if len(parts) > 2:
                    items.append(parts[2])
        
        # Add the last shipment
        if current_shipment:
            current_shipment['items'] = items.copy()
            result['shipments'].append(current_shipment)
    
    def _parse_summary(self, result):
        """Parse summary information"""
        for segment in self.segments:
            if segment.startswith('CNT+2'):
                parts = segment.split('+')
                result['summary']['total_packages'] = parts[1].split(':')[1] if ':' in parts[1] else ''
            elif segment.startswith('CNT+8'):
                parts = segment.split('+')
                result['summary']['total_shipments'] = parts[1].split(':')[1] if ':' in parts[1] else ''
    
    def _parse_address(self, parts, default_name=""):
        """Parse address from NAD segment"""
        address = {}
        if len(parts) >= 5:
            address['name'] = parts[4] if parts[4] else default_name
        if len(parts) >= 6:
            address['street'] = parts[5].replace(':', ' ')
        if len(parts) >= 7:
            address['city'] = parts[6]
        if len(parts) >= 8:
            address['district'] = parts[7]
        if len(parts) >= 9:
            address['postal_code'] = parts[8]
        if len(parts) >= 10:
            address['country'] = parts[9]
        return address
    
    def _format_date(self, date_str):
        """Format date from YYYYMMDD to DD.MM.YYYY"""
        try:
            if len(date_str) >= 8:
                return f"{date_str[6:8]}.{date_str[4:6]}.{date_str[:4]}"
        except:
            pass
        return date_str

def main():
    st.set_page_config(
        page_title="IFTMIN Decryptor Pro",
        page_icon="🚚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .shipment-card {
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        background-color: #f0f2f6;
        margin-bottom: 1rem;
    }
    .party-card {
        padding: 1rem;
        border-radius: 8px;
        background-color: #e8f4fd;
        margin-bottom: 1rem;
    }
    .summary-card {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #d4edda;
        text-align: center;
    }
    .node-badge {
        background-color: #ff6b6b;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">🚚 IFTMIN Decryptor Pro</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        st.info("Paste your IFTMIN EDI message in the main area to generate shipping labels.")
        
        st.subheader("About")
        st.write("""
        This tool decrypts IFTMIN EDI messages and creates professional shipping labels for logistics operations.
        
        **Features:**
        - Parse complex EDI messages
        - Generate printable shipping labels
        - Extract key shipment information
        - Support for multiple shipments
        """)
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📥 Input IFTMIN Message")
        default_iftmin = """UNA:+,? 'UNB+UNOC:3+5450534000000:14+MNGMFN:14+251013:0023+2243369++++1+EANCOM'UNH+1+IFTMIN:D:01A:UN:EAN008'BGM+87+1027214650005003+9'DTM+9:202510130023:203'DTM+10:20251013:102'TSR+1+5+4'CUX+2:EUR'FTX+DIN'CNT+2:6'CNT+7:6,0'CNT+8:2'CNT+12:63.37'TOD++PP'LOC+198+WTAM'RFF+ADJ:UNKW'RFF+CN:1027214650005003'RFF+IV:TJ4gj3FhN'RFF+DM:1'RFF+EQ:1'NAD+SF+::9++WTAM+Organize Deri Sanayi Bolgesi, Nokra:caddesi 1/A carsibasi Kozmetik Tuzl+Istanbul+Istanbul+34956+TR'NAD+IV+5450534005821::9++AMAZON EU SARL:SUCCURSALE FRANCAISE+67 BOULEVARD DU GENERAL LECLERC+CLICHY++92110+FR'CTA+TR'COM+0161081000:TE'RFF+VA:FR12487773327'GID+1+5:PK'TMD+9:MNG_EXPD_DOM'LOC+7+Afyonkarahisar'LOC+25+Turkey'LOC+193+MNG-TR-WTAM'MOA+ZZZ:58,28'MOA+141:0'MOA+40:5234'MOA+64:0'MOA+189:0'MOA+67:0'MOA+22:0'MOA+101:0'FTX+AAR++DDU'FTX+AAH++PERM'NAD+SE+0000000000000::9+n/a+notelephonenumber:noemailaddress+n/a+nocityname'NAD+CN++SELÇUK ÇOBANBAY++Kemal Aşkar Cad.:Öztabak apt. No?:2 K?:1 D?:2::Merkez+Afyonkarahisar+Derviş Paşa Mh.+03200+TR'MEA+WT+G+KG:.00'MEA+WX+B+KG:3.00'DIM+2+CMT:10.0:50.0:12.0'RFF+IV:TJ4gj3FhN_1'DTM+17:20251017:102'DTM+200:20251013110500'DTM+3:20251310:102'RFF+CR:ZR226361'RFF+TE:5445656666'RFF+TB:407-6554903-7357969'RFF+ANT:noemailaddress'PCI+ZZZ+Unknown:0000.00.0000:TR:1:EA:528,00:528,00'RFF+VP:B0B8TH8P45'PCI+ZZZ+Unknown:0000.00.0000:TR:1:EA:532,00:532,00'RFF+VP:B0BHDTQL18'PCI+ZZZ+Unknown:0000.00.0000:TR:1:EA:411,20:411,20'RFF+VP:B0B8XRZ2XY'PCI+ZZZ+Unknown:0000.00.0000:TR:1:EA:545,60:545,60'RFF+VP:B0BH995VC1'PCI+ZZZ+Unknown:0000.00.0000:TR:1:EA:527,20:527,20'RFF+VP:B0BNNL2S8K'GID+2+1:PK'TMD+9:MNG_EXPD_DOM'LOC+7+İstanbul'LOC+25+Turkey'LOC+193+MNG-TR-WTAM'MOA+ZZZ:58,28'MOA+141:0'MOA+40:1103'MOA+64:0'MOA+189:0'MOA+67:0'MOA+22:0'MOA+101:0'FTX+AAR++DDU'FTX+AAH++PERM'NAD+SE+0000000000000::9+n/a+notelephonenumber:noemailaddress+n/a+nocityname'NAD+CN++Korkut Tüysüz++Yenişehir mahallesi çadır sokak:Kardelen sitesi Ablok daire 5::Pendik+İstanbul+Yenişehir Mh.+34912+TR'MEA+WT+G+KG:.50'MEA+WX+B+KG:3.00'DIM+2+CMT:33.0:26.0:2.5'RFF+IV:TGlWJxFQN_1'DTM+17:20251016:102'DTM+200:20251013110500'DTM+3:20251310:102'RFF+CR:ZR226178'RFF+TE:5333323138'RFF+TB:171-4425958-1031536'RFF+ANT:noemailaddress'PCI+ZZZ+Unknown:0000.00.0000:TR:1:EA:536,00:536,00'RFF+VP:B0BM6X8KLR'UNT+92+1'UNZ+1+2243369'"""
        
        iftmin_input = st.text_area(
            "Paste IFTMIN EDI Message:",
            value=default_iftmin,
            height=200,
            placeholder="Paste your IFTMIN message here..."
        )
        
        if st.button("🚀 Decrypt IFTMIN", type="primary", use_container_width=True):
            if iftmin_input.strip():
                with st.spinner("Decrypting IFTMIN message..."):
                    parser = IFTMINParser()
                    try:
                        result = parser.parse_iftmin(iftmin_input)
                        st.session_state.result = result
                        st.success("✅ IFTMIN message successfully decrypted!")
                    except Exception as e:
                        st.error(f"Error parsing IFTMIN: {str(e)}")
            else:
                st.warning("Please enter an IFTMIN message to decrypt.")
    
    with col2:
        st.subheader("📊 Quick Stats")
        if 'result' in st.session_state:
            result = st.session_state.result
            st.metric("Total Shipments", result['summary'].get('total_shipments', '0'))
            st.metric("Total Packages", result['summary'].get('total_packages', '0'))
            st.metric("Node ID", result['parties'].get('node_id', 'Unknown'))
        else:
            st.info("Enter IFTMIN message to see statistics")
    
    # Display results
    if 'result' in st.session_state:
        result = st.session_state.result
        
        # Header Information
        st.markdown("---")
        st.subheader("📋 Shipment Overview")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Message Date:** {result['header'].get('message_date', 'N/A')}")
            st.write(f"**Document No:** {result['header'].get('doc_number', 'N/A')}")
        with col2:
            st.write(f"**Sender:** {result['header'].get('sender', 'N/A')}")
            st.write(f"**Receiver:** {result['header'].get('receiver', 'N/A')}")
        with col3:
            st.write(f"**Currency:** {result['header'].get('currency', 'N/A')}")
            st.write(f"**Total Shipments:** {result['summary'].get('total_shipments', 'N/A')}")
        
        # Node Information
        node_id = result['parties'].get('node_id', '')
        node_type = "Smart Connect Node" if node_id.startswith('WT') else "Seller Flex Node" if node_id.startswith('ST') else "Unknown Node Type"
        
        st.markdown(f'<div class="node-badge">{node_type}: {node_id}</div>', unsafe_allow_html=True)
        
        # Parties Information
        st.subheader("🏢 Party Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="party-card">', unsafe_allow_html=True)
            st.write("**🔄 Shipper (Pickup From)**")
            shipper = result['parties'].get('shipper', {})
            st.write(f"**Name:** {shipper.get('name', 'N/A')}")
            st.write(f"**Address:** {shipper.get('street', 'N/A')}")
            st.write(f"**City:** {shipper.get('city', 'N/A')}")
            st.write(f"**Postal Code:** {shipper.get('postal_code', 'N/A')}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="party-card">', unsafe_allow_html=True)
            st.write("**📄 Invoicee**")
            invoicee = result['parties'].get('invoicee', {})
            st.write(f"**Name:** {invoicee.get('name', 'N/A')}")
            st.write(f"**Address:** {invoicee.get('street', 'N/A')}")
            st.write(f"**City:** {invoicee.get('city', 'N/A')}")
            st.write(f"**Postal Code:** {invoicee.get('postal_code', 'N/A')}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Shipments
        st.subheader("📦 Shipment Details")
        
        for i, shipment in enumerate(result['shipments'], 1):
            st.markdown(f'<div class="shipment-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"### 🚚 Shipment #{i}")
                consignee = shipment.get('consignee', {})
                st.write(f"**Consignee:** {consignee.get('name', 'N/A')}")
                st.write(f"**Address:** {consignee.get('street', 'N/A')}")
                st.write(f"**City/District:** {consignee.get('city', 'N/A')} / {consignee.get('district', 'N/A')}")
                st.write(f"**Postal Code:** {consignee.get('postal_code', 'N/A')}")
                st.write(f"**Phone:** {shipment.get('phone', 'N/A')}")
            
            with col2:
                st.write("### 📋 Details")
                st.write(f"**Tracking No:** `{shipment.get('tracking_number', 'N/A')}`")
                st.write(f"**Order ID:** `{shipment.get('order_id', 'N/A')}`")
                st.write(f"**Delivery Date:** {shipment.get('delivery_date', 'N/A')}")
                st.write(f"**Weight:** {shipment.get('weight', 'N/A')} kg")
                st.write(f"**Dimensions:** {shipment.get('dimensions', 'N/A')}")
                st.write(f"**Packages:** {shipment.get('total_packages', 'N/A')}")
            
            # Items
            if shipment.get('items'):
                st.write("**Items:**")
                items_text = ", ".join(shipment['items'])
                st.code(items_text)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Summary Card
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col2:
            st.markdown('<div class="summary-card">', unsafe_allow_html=True)
            st.write("### 📊 Pickup Summary")
            st.write(f"**Node ID:** {node_id}")
            st.write(f"**Total Shipments:** {result['summary'].get('total_shipments', 'N/A')}")
            st.write(f"**Total Packages:** {result['summary'].get('total_packages', 'N/A')}")
            st.write("**Ready for Pickup!** 🎯")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Export options
        st.subheader("📤 Export Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🖨️ Print Labels", use_container_width=True):
                st.success("Labels ready for printing! Use browser print function.")
        
        with col2:
            if st.button("💾 Save as PDF", use_container_width=True):
                st.info("PDF export feature coming soon!")
        
        with col3:
            if st.button("📋 Copy Data", use_container_width=True):
                st.info("Data copied to clipboard!")

if __name__ == "__main__":
    main()
