import React from 'react';
import footerCharacter from '../../assets/images/footer_character.png';

const Footer = () => {
  return (
    <footer
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        width: '100%',
        height: 'auto',
        maxHeight: '130px',
        overflow: 'visible',
        backgroundColor: '#1C8BE7',
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'center',
        paddingRight: '0px',
        zIndex: 0,
        pointerEvents: 'none'
      }}
    >
      {/* Footer content goes here */}
      <div style={{ padding: '10px 20px', color: 'white', textAlign: 'center' }}>
        © 2026 Easy Welfare Guide. All rights reserved.
      </div>
      
      {/* Footer image on the right */}
      <img 
        src={footerCharacter} 
        alt="Footer Character" 
        style={{
          height: '40px',
          width: 'auto',
          objectFit: 'contain',
          marginRight: '-15px',
          position: 'absolute',
          right: 0,
          zIndex: 10
        }}
      />
    </footer>
  );
};

export default Footer;
