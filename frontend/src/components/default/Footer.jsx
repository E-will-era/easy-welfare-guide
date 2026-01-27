import React from 'react';

const Footer = () => {
  return (
    <footer
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        width: '100%',
        height: 'auto',
        maxHeight: '100px',
        overflow: 'visible',
        backgroundColor: '#1C8BE7',
        display: 'flex',
        alignItems: 'end',
        justifyContent: 'center',
        zIndex: 0,
        pointerEvents: 'none'
      }}
    >
      {/* Footer content goes here */}
      <div style={{ padding: '10px 20px', color: 'white', textAlign: 'center' }}>
        © 2026 Easy Welfare Guide. All rights reserved.
      </div>
    </footer>
  );
};

export default Footer;
